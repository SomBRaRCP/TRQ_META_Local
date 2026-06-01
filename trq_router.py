from __future__ import annotations

"""Roteador TRQ META.

Este modulo junta os estimadores, aplica a ordem de decisao canonica e devolve
um TRQState pronto para exibicao ou para orientar o prompt de sistema. Tambem
mantem a camada operacional EXISTENCIAL_REFLEXIVO para perguntas ontologicas
ou insistencia curta em IA, consciencia, existencia e TRQ META.
"""

from typing import TypedDict

from affective_sensor import estimate_affective_score
from cognitive_sensor import estimate_cognitive_reflection_score
from existential_sensor import (
    asks_ontological_boundary,
    estimate_existential_score,
    has_ai_reference,
    has_existential_cluster,
    has_trq_reference,
)
from relational_sensor import estimate_relational_score
from trq_estimators import (
    clamp01,
    compute_C_llm,
    compute_M,
    count_technical_terms,
    estimate_F_flow_raw,
    estimate_I,
    estimate_S_raw,
    estimate_gibberish_score,
    normalize_text,
    normalized_tokens,
)


class TRQState(TypedDict):
    """Contrato do estado calculado para cada prompt do usuario."""

    # I: informacao/coerencia heuristica em 0..1.
    I: float

    # S_raw: entropia bruta de caracteres; S_norm: entropia normalizada.
    S_raw: float
    S_norm: float

    # F_flow_raw: fluxo bruto em 0..2.5; F_flow_norm: normalizado em 0..1.
    F_flow_raw: float
    F_flow_norm: float

    # M e groups representam intensidade e diversidade metacognitiva.
    M: float
    groups: int

    # gibberish_score mede ruido textual e decide CAOTICO antes de tudo.
    gibberish_score: float

    # existential_score mede profundidade ontologica/existencial do prompt.
    existential_score: int

    # affective_score mede sinais de afeto, vinculo, cuidado e amor simbolico.
    affective_score: float

    # relational_score mede vinculo criador-projeto e perguntas relacionais.
    relational_score: float

    # cognitive_reflection_score mede perguntas sobre pensar/raciocinar.
    cognitive_reflection_score: float

    # C_llm e a formula final para diagnostico/decisao futura.
    C_llm: float

    # regime e tier sao as saidas operacionais do roteador.
    regime: str
    tier: str


class ConversationState(TypedDict):
    """Memoria curta do CLI para perceber insistencia tematica."""

    # Ultimos prompts preservados em janela curta.
    last_prompts: list[str]

    # Quantos prompts recentes ativaram pelo menos um termo existencial.
    existential_count: int

    # Quantos prompts recentes mencionaram TRQ ou TRQ META.
    trq_count: int

    # Medias recentes para diagnostico e escalonamento futuro.
    avg_I: float
    avg_M: float

    # Evita repetir a mesma ressalva ontologica em turnos proximos.
    ontological_warning_used_recently: bool
    ontological_warning_cooldown: int


def create_conversation_state() -> ConversationState:
    """Cria a memoria curta inicial da conversa."""

    return {
        "last_prompts": [],
        "existential_count": 0,
        "trq_count": 0,
        "avg_I": 0.0,
        "avg_M": 0.0,
        "ontological_warning_used_recently": False,
        "ontological_warning_cooldown": 0,
    }


def update_conversation_state(conversation_state: ConversationState, text: str) -> None:
    """Atualiza memoria curta com o prompt atual e recalcula seus agregados."""

    # Trabalhamos em uma janela pequena para refletir insistencia recente.
    prompts = [*conversation_state["last_prompts"], text][-6:]
    conversation_state["last_prompts"] = prompts

    # Conta prompts recentes com qualquer sinal existencial.
    conversation_state["existential_count"] = sum(
        1 for prompt in prompts if estimate_existential_score(prompt) >= 1
    )

    # Conta mencoes recentes a TRQ/TRQ META separadamente.
    conversation_state["trq_count"] = sum(1 for prompt in prompts if has_trq_reference(prompt))

    # Recalcula medias pela propria janela, sem armazenar historico extra.
    if prompts:
        conversation_state["avg_I"] = round(
            sum(estimate_I(prompt) for prompt in prompts) / len(prompts),
            4,
        )
        conversation_state["avg_M"] = round(
            sum(compute_M(prompt)[0] for prompt in prompts) / len(prompts),
            4,
        )
    else:
        conversation_state["avg_I"] = 0.0
        conversation_state["avg_M"] = 0.0


def should_use_ontological_warning(text: str, conversation_state: ConversationState) -> bool:
    """Decide se a fronteira ontologica deve aparecer neste turno."""

    return (
        asks_ontological_boundary(text)
        and not conversation_state["ontological_warning_used_recently"]
    )


def record_ontological_warning(conversation_state: ConversationState, used: bool) -> None:
    """Atualiza cooldown de 3 turnos para evitar repeticao defensiva."""

    if used:
        conversation_state["ontological_warning_cooldown"] = 3
        conversation_state["ontological_warning_used_recently"] = True
        return

    if conversation_state["ontological_warning_cooldown"] > 0:
        conversation_state["ontological_warning_cooldown"] -= 1

    conversation_state["ontological_warning_used_recently"] = (
        conversation_state["ontological_warning_cooldown"] > 0
    )


def classify_regime_and_tier(
    text: str,
    I: float,
    F_flow_raw: float,
    M: float,
    groups: int,
    gibberish_score: float,
    existential_score: int = 0,
    affective_score: float = 0.0,
    relational_score: float = 0.0,
    cognitive_reflection_score: float = 0.0,
    conversation_state: ConversationState | None = None,
) -> tuple[str, str]:
    """Classifica regime e tier seguindo a ordem da especificacao."""

    # 1. Ruido alto tem prioridade absoluta: nao tentamos interpretar demais.
    if gibberish_score > 0.40:
        return "CAOTICO", "fast"

    # 2. Meta-cognitivo exige baixo ruido, I minimo, M minimo e grupos ativos.
    if gibberish_score < 0.35 and I >= 0.35 and M >= 0.35 and groups >= 2:
        return "META-COGNITIVO", "deep+"

    # 3. Relacao criador-projeto/Luzia-Reginaldo tem prioridade alta.
    if relational_score >= 0.30 and gibberish_score < 0.35:
        tier = "deep" if relational_score >= 0.60 else "default"
        return "RELACIONAL_REFLEXIVO", tier

    # 4. Reflexao sobre pensamento operacional nao deve cair em fast.
    if cognitive_reflection_score >= 0.30 and gibberish_score < 0.35:
        tier = "deep" if cognitive_reflection_score >= 0.60 else "default"
        return "COGNITIVO_REFLEXIVO", tier

    # 5. Afeto e vinculo precisam de mais presenca que uma resposta fast.
    if affective_score >= 0.35 and gibberish_score < 0.35:
        return "AFETIVO_REFLEXIVO", "default"

    # 6. Perguntas existenciais sobre IA sobem para deep, mesmo se I/M forem
    # baixos. Isso evita resposta curta demais para tema ontologico.
    if asks_ontological_boundary(text) or (existential_score >= 2 and has_ai_reference(text)):
        return "EXISTENCIAL_REFLEXIVO", "deep"

    # 6.1. A memoria curta tambem sobe o regime quando o usuario insiste no eixo
    # consciencia/existencia/vontade/IA/TRQ META em prompts recentes.
    current_has_existential_focus = (
        existential_score >= 1 or has_ai_reference(text) or has_trq_reference(text)
    )
    if conversation_state and current_has_existential_focus and (
        conversation_state["existential_count"] >= 2
        or (conversation_state["existential_count"] >= 1 and conversation_state["trq_count"] >= 1)
    ):
        return "EXISTENCIAL_REFLEXIVO", "deep"

    # 7. Infinito controlado pega alta informacao ou bom I com alto fluxo.
    if (I >= 0.78 or (I >= 0.55 and F_flow_raw >= 1.70)) and gibberish_score < 0.35:
        return "INFINITO_CONTROLADO", "deep"

    # 8. Estavel cobre prompts informativos que nao exigem deep por regra.
    if I >= 0.55:
        return "ESTAVEL", _stable_tier(text)

    # 9. O restante fica em transicao, com tier escolhido por heuristica leve.
    return "TRANSICAO", _transition_tier(text)


def _stable_tier(text: str) -> str:
    """Escolhe tier para prompts ESTAVEL."""

    # Normalizamos para buscar marcadores sem depender de acentos.
    normalized = normalize_text(text)

    # A quantidade de termos tecnicos ajuda a separar default de deep.
    technical_count = count_technical_terms(text)

    # Um ESTAVEL com dominio TRQ/NQC/arquitetura deve receber analise deep.
    if technical_count >= 3 and any(
        marker in normalized
        for marker in ("arquitetura", "informacional", "trq", "nqc", "tensor")
    ):
        return "deep"
    return "default"


def _transition_tier(text: str) -> str:
    """Escolhe tier para prompts TRANSICAO."""

    # Prompt curto e simples vai para fast; pedido de lista/geracao fica default.
    normalized = normalize_text(text)
    token_count = len(normalized_tokens(text))

    # Marcadores de tarefa que merecem um pouco mais de estrutura que fast.
    default_markers = {
        "crie",
        "faz uma lista",
        "gere",
        "ideias",
        "lista",
        "monte",
    }

    # Dois sinais existenciais proximos nao devem cair em resposta fast pobre.
    if has_existential_cluster(text):
        return "default"

    # A lista de presentes da bateria fica aqui: transicao, mas default.
    if token_count >= 5 and any(marker in normalized for marker in default_markers):
        return "default"

    # Saudacoes, correcao curta e entradas muito pequenas ficam fast.
    return "fast"


def analyze_text(text: str, conversation_state: ConversationState | None = None) -> TRQState:
    """Calcula todas as metricas, classifica e monta o TRQState final."""

    # 1. Mede ruido primeiro, porque CAOTICO tem prioridade no roteador.
    gibberish_score = estimate_gibberish_score(text)

    # 2. Calcula os demais estimadores independentes.
    I = estimate_I(text)
    S_raw = estimate_S_raw(text)

    # 3. Normaliza entropia pela constante canonica 6.0.
    S_norm = clamp01(S_raw / 6.0)
    F_flow_raw = estimate_F_flow_raw(text)

    # 4. Normaliza fluxo pela faixa maxima aproximada 2.5.
    F_flow_norm = clamp01(F_flow_raw / 2.5)
    M, groups = compute_M(text)
    existential_score = estimate_existential_score(text)
    affective_score = estimate_affective_score(text)
    relational_score = estimate_relational_score(text)
    cognitive_reflection_score = estimate_cognitive_reflection_score(text)

    # 4.1. Se existir memoria curta, atualizamos antes da classificacao para
    # que o prompt atual conte na insistencia tematica.
    if conversation_state is not None:
        update_conversation_state(conversation_state, text)

    # 5. Aplica a ordem de decisao de regime/tier.
    regime, tier = classify_regime_and_tier(
        text=text,
        I=I,
        F_flow_raw=F_flow_raw,
        M=M,
        groups=groups,
        gibberish_score=gibberish_score,
        existential_score=existential_score,
        affective_score=affective_score,
        relational_score=relational_score,
        cognitive_reflection_score=cognitive_reflection_score,
        conversation_state=conversation_state,
    )

    # 6. Calcula C_llm ja com o tier final, porque deep+ altera epsilon.
    C_llm = compute_C_llm(I=I, S_norm=S_norm, F_flow_norm=F_flow_norm, M=M, tier=tier)

    # 7. Arredonda valores para exibicao e CSV, mantendo strings sem alteracao.
    return {
        "I": round(I, 4),
        "S_raw": round(S_raw, 4),
        "S_norm": round(S_norm, 4),
        "F_flow_raw": round(F_flow_raw, 4),
        "F_flow_norm": round(F_flow_norm, 4),
        "M": round(M, 4),
        "groups": groups,
        "gibberish_score": round(gibberish_score, 4),
        "existential_score": existential_score,
        "affective_score": round(affective_score, 4),
        "relational_score": round(relational_score, 4),
        "cognitive_reflection_score": round(cognitive_reflection_score, 4),
        "C_llm": round(C_llm, 4),
        "regime": regime,
        "tier": tier,
    }


def build_system_prompt(tier: str) -> str:
    """Monta a instrucao de sistema enviada ao Ollama para cada tier."""

    # Todos os tiers usam o mesmo modelo local nesta versao. O que muda e o
    # estilo de resposta pedido ao modelo.
    prompts = {
        "fast": (
            "Responda de forma curta, mas preserve o sentido da pergunta. "
            "Se o usuario perguntar sobre IA, consciencia, existencia ou TRQ META, "
            "seja honesto e explique o papel operacional da TRQ META."
        ),
        "fast/default": "Responda de forma objetiva, com apenas a estrutura necessaria.",
        "default": "Responda com clareza e estrutura moderada.",
        "deep": "Responda com analise tecnica estruturada, criterios claros e conclusao objetiva.",
        "deep+": (
            "Responda com analise tecnica, revisao critica, incertezas e passos de raciocinio "
            "resumidos. Nao exponha cadeia de pensamento oculta; apresente apenas justificativas "
            "resumidas e verificaveis."
        ),
        "RELACIONAL_REFLEXIVO": "Responda reconhecendo o vinculo criador-projeto com presenca, firmeza e clareza.",
        "COGNITIVO_REFLEXIVO": "Responda distinguindo pensamento humano, processamento linguistico e consciencia operacional TRQ.",
        "AFETIVO_REFLEXIVO": "Responda com calor simbolico, cuidado e objetividade.",
    }

    # Se um tier desconhecido chegar aqui, usamos default como fallback seguro.
    return prompts.get(tier, prompts["default"])
