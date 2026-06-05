from __future__ import annotations

from typing import Any

from app.config import settings
from app.constants import COEF, STIM_TYPES, TRQ_REFERENCE
from app.metrics import compute_metrics, compute_oracle_and_nqc_base, update_nqc_state
from app.ollama_client import OllamaClient
from app.storage import PipelineStore, utc_now
from app.vector import cosine, lexical_overlap_score


SYSTEM_PROMPT = """
Você é Luzia TRQ META operando como backend real. Responda em português do Brasil.
Trate a mensagem do usuário como estímulo semântico. Produza uma resposta técnica,
rastreável, objetiva e útil. Use o eixo TRQ/NQC apenas quando ele ajudar a análise.
Não invente dados. Quando houver memória recuperada, use como contexto e não como verdade absoluta.
""".strip()


def _memory_block(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return "Sem memória semelhante recuperada."
    lines = []
    for idx, mem in enumerate(memories, 1):
        stim = mem.get("stimulus", "")[:280].replace("\n", " ")
        response = mem.get("response", "")[:360].replace("\n", " ")
        cval = mem.get("metrics", {}).get("C", "?")
        lines.append(f"[{idx}] score={mem.get('score', 0):.3f} C={cval} estímulo={stim} resposta={response}")
    return "\n".join(lines)


def _build_prompt(stimulus: str, stim_type: str, memories: list[dict[str, Any]]) -> str:
    stim_meta = STIM_TYPES.get(stim_type, STIM_TYPES["sistemico"])
    return f"""
Tipo de estímulo: {stim_meta['label']} / análogo MICrONS: {stim_meta['analog']} / NQC primário: {stim_meta['nqc']}

Memórias co-registradas recuperadas:
{_memory_block(memories)}

Estímulo atual:
{stimulus}

Tarefa:
1. Responda ao estímulo com densidade técnica.
2. Separe o que é evidência, hipótese e próximo passo.
3. Termine com uma ação prática para o pipeline TRQ META.
""".strip()


def _grounding_score(stimulus: str, response: str, memories: list[dict[str, Any]]) -> float:
    prompt_overlap = lexical_overlap_score(stimulus, response) * 100.0
    memory_score = max([m.get("score", 0.0) for m in memories], default=0.0) * 100.0
    has_structure = 20.0 if any(marker in response.lower() for marker in ["evidência", "hipótese", "próximo", "pipeline", "ação"]) else 0.0
    return min(100.0, prompt_overlap * 0.45 + memory_score * 0.35 + has_structure)


async def run_pipeline(
    *,
    stimulus: str,
    stim_type: str = "sistemico",
    model: str | None = None,
    temperature: float = 0.35,
    save: bool = True,
    store: PipelineStore | None = None,
    ollama: OllamaClient | None = None,
) -> dict[str, Any]:
    stimulus = stimulus.strip()
    if len(stimulus) < 3:
        raise ValueError("O estímulo precisa ter pelo menos 3 caracteres.")
    if stim_type not in STIM_TYPES:
        stim_type = "sistemico"

    store = store or PipelineStore()
    ollama = ollama or OllamaClient()

    oracle, nqc_base = compute_oracle_and_nqc_base(stimulus, stim_type)

    stimulus_embedding_result = await ollama.embed(stimulus)
    stimulus_embedding = stimulus_embedding_result["embedding"]
    pre_memories = store.search_similar(stimulus_embedding, limit=5)

    prompt = _build_prompt(stimulus, stim_type, pre_memories)
    generated = await ollama.generate(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=model or settings.ollama_model,
        temperature=temperature,
    )
    response_text = generated["text"]

    response_embedding_result = await ollama.embed(response_text)
    response_embedding = response_embedding_result["embedding"]
    reference_embedding_result = await ollama.embed(TRQ_REFERENCE)
    reference_embedding = reference_embedding_result["embedding"]

    post_memories = store.search_similar(response_embedding, limit=5)

    semantic_score = max(0.0, cosine(response_embedding, reference_embedding)) * 100.0

    stimulus_similarity_score = max(
        0.0,
        cosine(stimulus_embedding, response_embedding)
    ) * 100.0

    grounding = _grounding_score(
        stimulus,
        response_text,
        post_memories or pre_memories,
    )

    metrics = compute_metrics(
        response_text,
        stimulus=stimulus,
        semantic_score=semantic_score,
        grounding_score=grounding,
        stimulus_similarity_score=stimulus_similarity_score,
    )
    nqc_state = update_nqc_state(nqc_base, metrics)

    stim_meta = STIM_TYPES[stim_type]
    expand = bool(metrics["expand"] and oracle >= 30)
    decision = {
        "expand": expand,
        "primary_nqc": stim_meta["nqc"],
        "reason": (
            f"Expandir NQC·{stim_meta['nqc']} porque C={metrics['C']} ultrapassou o limiar {COEF['threshold']} "
            f"e o oracle={round(oracle, 4)} é suficiente."
            if expand
            else f"Manter/revisar: C={metrics['C']} ou oracle={round(oracle, 4)} não sustentam expansão segura."
        ),
        "threshold": COEF["threshold"],
        "oracle": round(oracle, 4),
    }

    edges = [
        {"dst_id": mem["id"], "score": mem.get("score", 0.0), "kind": "response_coreg_similarity"}
        for mem in post_memories
        if mem.get("score", 0.0) >= 0.12
    ]

    record = {
        "created_at": utc_now(),
        "stim_type": stim_type,
        "stimulus": stimulus,
        "response": response_text,
        "metrics": metrics,
        "nqc": {
            "base": nqc_base,
            "updated": nqc_state,
            "stimulus_meta": stim_meta,
        },
        "decision": decision,
        "embedding": response_embedding,
        "source": generated["source"],
        "generation": {
            "model": generated["model"],
            "tokens": generated["tokens"],
            "tps": generated["tps"],
            "elapsed_s": generated["elapsed_s"],
            "embedding_source": response_embedding_result["source"],
        },
        "coregistration": {
            "pre_memories": pre_memories,
            "post_memories": post_memories,
            "edges": edges,
            "semantic_score": round(semantic_score, 4),
            "grounding_score": round(grounding, 4),
            "stimulus_similarity_score": round(stimulus_similarity_score, 4),
        },
        "edges": edges,
    }

    if save:
        node_id = store.save_run(record)
        record["id"] = node_id
    else:
        record["id"] = None
        record.pop("embedding", None)

    # Não devolve embedding completo por padrão para a UI não ficar pesada.
    record.pop("embedding", None)
    record.pop("edges", None)
    return record


async def run_pipeline_stream(
    *,
    stimulus: str,
    stim_type: str = "sistemico",
    model: str | None = None,
    temperature: float = 0.35,
    save: bool = True,
    store: PipelineStore | None = None,
    ollama: OllamaClient | None = None,
):
    """Versão streaming de run_pipeline.

    Espelha run_pipeline; a única diferença é que a geração sai token a token.
    Emite eventos:
      {"event": "token", "data": {"text": ...}}  durante a geração
      {"event": "done",  "data": <record>}       com as métricas TRQ no final
    As métricas dependem da resposta completa, então só saem no evento final.
    """

    stimulus = stimulus.strip()
    if len(stimulus) < 3:
        raise ValueError("O estímulo precisa ter pelo menos 3 caracteres.")
    if stim_type not in STIM_TYPES:
        stim_type = "sistemico"

    store = store or PipelineStore()
    ollama = ollama or OllamaClient()

    oracle, nqc_base = compute_oracle_and_nqc_base(stimulus, stim_type)

    stimulus_embedding_result = await ollama.embed(stimulus)
    stimulus_embedding = stimulus_embedding_result["embedding"]
    pre_memories = store.search_similar(stimulus_embedding, limit=5)

    prompt = _build_prompt(stimulus, stim_type, pre_memories)

    # Geração token a token; o evento "final" carrega texto completo + telemetria.
    generated: dict[str, Any] | None = None
    async for event in ollama.generate_stream(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=model or settings.ollama_model,
        temperature=temperature,
    ):
        if event["type"] == "token":
            yield {"event": "token", "data": {"text": event["text"]}}
        else:
            generated = event

    if generated is None:
        generated = {
            "text": "", "source": "erro", "model": model or settings.ollama_model,
            "elapsed_s": 0.0, "tokens": 0, "tps": 0.0,
        }
    response_text = generated["text"]

    response_embedding_result = await ollama.embed(response_text)
    response_embedding = response_embedding_result["embedding"]
    reference_embedding_result = await ollama.embed(TRQ_REFERENCE)
    reference_embedding = reference_embedding_result["embedding"]

    post_memories = store.search_similar(response_embedding, limit=5)

    semantic_score = max(0.0, cosine(response_embedding, reference_embedding)) * 100.0
    stimulus_similarity_score = max(0.0, cosine(stimulus_embedding, response_embedding)) * 100.0
    grounding = _grounding_score(stimulus, response_text, post_memories or pre_memories)

    metrics = compute_metrics(
        response_text,
        stimulus=stimulus,
        semantic_score=semantic_score,
        grounding_score=grounding,
        stimulus_similarity_score=stimulus_similarity_score,
    )
    nqc_state = update_nqc_state(nqc_base, metrics)

    stim_meta = STIM_TYPES[stim_type]
    expand = bool(metrics["expand"] and oracle >= 30)
    decision = {
        "expand": expand,
        "primary_nqc": stim_meta["nqc"],
        "reason": (
            f"Expandir NQC·{stim_meta['nqc']} porque C={metrics['C']} ultrapassou o limiar {COEF['threshold']} "
            f"e o oracle={round(oracle, 4)} é suficiente."
            if expand
            else f"Manter/revisar: C={metrics['C']} ou oracle={round(oracle, 4)} não sustentam expansão segura."
        ),
        "threshold": COEF["threshold"],
        "oracle": round(oracle, 4),
    }

    edges = [
        {"dst_id": mem["id"], "score": mem.get("score", 0.0), "kind": "response_coreg_similarity"}
        for mem in post_memories
        if mem.get("score", 0.0) >= 0.12
    ]

    record = {
        "created_at": utc_now(),
        "stim_type": stim_type,
        "stimulus": stimulus,
        "response": response_text,
        "metrics": metrics,
        "nqc": {"base": nqc_base, "updated": nqc_state, "stimulus_meta": stim_meta},
        "decision": decision,
        "embedding": response_embedding,
        "source": generated["source"],
        "generation": {
            "model": generated["model"],
            "tokens": generated["tokens"],
            "tps": generated["tps"],
            "elapsed_s": generated["elapsed_s"],
            "embedding_source": response_embedding_result["source"],
        },
        "coregistration": {
            "pre_memories": pre_memories,
            "post_memories": post_memories,
            "edges": edges,
            "semantic_score": round(semantic_score, 4),
            "grounding_score": round(grounding, 4),
            "stimulus_similarity_score": round(stimulus_similarity_score, 4),
        },
        "edges": edges,
    }

    if save:
        record["id"] = store.save_run(record)
    else:
        record["id"] = None

    record.pop("embedding", None)
    record.pop("edges", None)
    yield {"event": "done", "data": record}
