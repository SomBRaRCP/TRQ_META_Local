from __future__ import annotations

"""TRQ Persistent Memory Layer.

Memoria local revisavel em JSON/Markdown. Esta camada nao altera o modelo
Ollama; ela recupera contexto e registra preferencias/correcoes explicitas.
"""

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import BASE_DIR
from trq_estimators import normalize_text


MEMORY_DIR = BASE_DIR / "memory"
RAW_CONVERSATIONS_DIR = MEMORY_DIR / "raw_conversations"
LONG_TERM_MEMORY_PATH = MEMORY_DIR / "long_term_memory.json"
CREATOR_MEMORY_PATH = MEMORY_DIR / "creator_profile_memory.json"
PREFERENCES_PATH = MEMORY_DIR / "luzia_preferences.json"
CORRECTIONS_PATH = MEMORY_DIR / "corrections_log.json"
SUMMARIES_PATH = MEMORY_DIR / "conversation_summaries.md"

MEMORY_TYPES = {
    "preference",
    "correction",
    "creator",
    "project",
    "symbolic",
    "technical",
    "relationship",
}

TYPE_TO_PATH = {
    "preference": PREFERENCES_PATH,
    "correction": CORRECTIONS_PATH,
    "creator": CREATOR_MEMORY_PATH,
    "project": LONG_TERM_MEMORY_PATH,
    "symbolic": LONG_TERM_MEMORY_PATH,
    "technical": LONG_TERM_MEMORY_PATH,
    "relationship": LONG_TERM_MEMORY_PATH,
}

EXPLICIT_MEMORY_MARKERS = {
    "daqui para frente",
    "de agora em diante",
    "guarde",
    "lembre",
    "prefiro que",
    "quero que voce",
    "registre",
    "salve",
}

CORRECTION_MARKERS = {
    "fale desse jeito",
    "isso ficou errado",
    "isso ficou frio",
    "nao faca mais isso",
    "nao responda assim",
    "pare de repetir",
    "quero mais firmeza",
    "quero mais presenca",
}


def now_iso() -> str:
    """Retorna timestamp UTC em ISO."""

    return datetime.now(timezone.utc).isoformat()


def ensure_memory_files() -> None:
    """Cria pasta e arquivos de memoria se ainda nao existirem."""

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    RAW_CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_CONVERSATIONS_DIR / ".gitkeep").touch(exist_ok=True)

    for path in (
        LONG_TERM_MEMORY_PATH,
        CREATOR_MEMORY_PATH,
        PREFERENCES_PATH,
        CORRECTIONS_PATH,
    ):
        if not path.exists():
            save_json(path, [])

    if not SUMMARIES_PATH.exists():
        SUMMARIES_PATH.write_text("# Conversation Summaries\n\n", encoding="utf-8")


def load_json(path: Path | str, default: Any) -> Any:
    """Carrega JSON com fallback se arquivo nao existir ou estiver corrompido."""

    json_path = Path(path)
    if not json_path.exists():
        return default

    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        corrupt_path = json_path.with_suffix(json_path.suffix + ".corrupt")
        try:
            shutil.copy2(json_path, corrupt_path)
        except OSError:
            pass
        return default


def save_json(path: Path | str, data: Any) -> None:
    """Salva JSON criando backup .bak antes de sobrescrever."""

    json_path = Path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    if json_path.exists():
        shutil.copy2(json_path, json_path.with_suffix(json_path.suffix + ".bak"))

    json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _memory_path(memory_type: str) -> Path:
    if memory_type not in MEMORY_TYPES:
        raise ValueError(f"tipo de memoria invalido: {memory_type}")
    return TYPE_TO_PATH[memory_type]


def _all_memory_paths() -> list[Path]:
    return [
        LONG_TERM_MEMORY_PATH,
        CREATOR_MEMORY_PATH,
        PREFERENCES_PATH,
        CORRECTIONS_PATH,
    ]


def _new_memory(
    memory_type: str,
    content: str,
    source: str,
    confidence: float,
    tags: list[str] | None,
) -> dict[str, Any]:
    timestamp = now_iso()
    return {
        "id": str(uuid.uuid4()),
        "type": memory_type,
        "content": content.strip(),
        "source": source,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "tags": tags or [],
        "active": True,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def add_memory(
    memory_type: str,
    content: str,
    source: str = "conversation",
    confidence: float = 0.8,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Adiciona memoria revisavel."""

    ensure_memory_files()
    if not content.strip():
        raise ValueError("conteudo de memoria vazio")

    path = _memory_path(memory_type)
    memories = load_json(path, [])
    memory = _new_memory(memory_type, content, source, confidence, tags)
    memories.append(memory)
    save_json(path, memories)
    return memory


def list_memories(memory_type: str | None = None) -> list[dict[str, Any]]:
    """Lista memorias ativas, opcionalmente por tipo."""

    ensure_memory_files()
    paths = [_memory_path(memory_type)] if memory_type else _all_memory_paths()
    memories: list[dict[str, Any]] = []
    for path in paths:
        memories.extend(load_json(path, []))
    return [mem for mem in memories if mem.get("active", True)]


def search_memories(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Busca simples por sobreposicao de termos em conteudo/tags/tipo."""

    normalized_query = normalize_text(query)
    query_terms = {term for term in normalized_query.split() if len(term) >= 3}
    if not query_terms:
        return list_memories()[:limit]

    scored: list[tuple[int, dict[str, Any]]] = []
    for memory in list_memories():
        haystack = normalize_text(
            " ".join(
                [
                    str(memory.get("type", "")),
                    str(memory.get("content", "")),
                    " ".join(memory.get("tags", [])),
                ]
            )
        )
        score = sum(1 for term in query_terms if term in haystack)
        if score > 0:
            scored.append((score, memory))

    scored.sort(key=lambda item: (item[0], item[1].get("confidence", 0.0)), reverse=True)
    return [memory for _, memory in scored[:limit]]


def _find_memory(memory_id: str) -> tuple[Path, list[dict[str, Any]], dict[str, Any]] | None:
    for path in _all_memory_paths():
        memories = load_json(path, [])
        for memory in memories:
            if str(memory.get("id", "")).startswith(memory_id):
                return path, memories, memory
    return None


def deactivate_memory(memory_id: str) -> bool:
    """Desativa memoria por id completo ou prefixo."""

    ensure_memory_files()
    found = _find_memory(memory_id)
    if not found:
        return False
    path, memories, memory = found
    memory["active"] = False
    memory["updated_at"] = now_iso()
    save_json(path, memories)
    return True


def update_memory(
    memory_id: str,
    new_content: str | None = None,
    confidence: float | None = None,
    active: bool | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any] | None:
    """Atualiza memoria por id completo ou prefixo."""

    ensure_memory_files()
    found = _find_memory(memory_id)
    if not found:
        return None
    path, memories, memory = found

    if new_content is not None:
        memory["content"] = new_content.strip()
    if confidence is not None:
        memory["confidence"] = max(0.0, min(1.0, float(confidence)))
    if active is not None:
        memory["active"] = active
    if tags is not None:
        memory["tags"] = tags
    memory["updated_at"] = now_iso()

    save_json(path, memories)
    return memory


def add_correction(error: str, correction: str, source: str = "user") -> dict[str, Any]:
    """Adiciona correcao explicita."""

    content = f"Erro: {error.strip()} | Correcao: {correction.strip()}"
    return add_memory(
        "correction",
        content,
        source=source,
        confidence=0.95,
        tags=["correcao", "luzia"],
    )


def add_preference(content: str, confidence: float = 0.9) -> dict[str, Any]:
    """Adiciona preferencia manual de Reginaldo."""

    return add_memory(
        "preference",
        content,
        source="user_explicit",
        confidence=confidence,
        tags=["preferencia", "reginaldo", "luzia"],
    )


def add_creator_memory(content: str, confidence: float = 0.9) -> dict[str, Any]:
    """Adiciona memoria sobre o criador."""

    return add_memory(
        "creator",
        content,
        source="user_explicit",
        confidence=confidence,
        tags=["criador", "reginaldo"],
    )


def append_conversation_summary(summary: str) -> None:
    """Acrescenta resumo curto ao Markdown de resumos."""

    ensure_memory_files()
    with SUMMARIES_PATH.open("a", encoding="utf-8") as summary_file:
        summary_file.write(f"\n## {now_iso()}\n\n{summary.strip()}\n")


def save_raw_turn(
    user_prompt: str,
    metrics: dict[str, Any],
    body_state: dict[str, Any],
    response: str,
) -> Path:
    """Salva turno bruto em JSON dentro de raw_conversations."""

    ensure_memory_files()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = RAW_CONVERSATIONS_DIR / f"{timestamp}_{uuid.uuid4().hex[:8]}.json"
    save_json(
        path,
        {
            "id": str(uuid.uuid4()),
            "created_at": now_iso(),
            "user_prompt": user_prompt,
            "metrics": metrics,
            "body_state": body_state,
            "response": response,
        },
    )
    return path


def infer_memory_from_user_prompt(prompt: str) -> list[dict[str, Any]]:
    """Sugere memorias apenas quando ha pedido explicito ou correcao clara."""

    normalized = normalize_text(prompt)
    suggestions: list[dict[str, Any]] = []

    explicit = any(marker in normalized for marker in EXPLICIT_MEMORY_MARKERS)
    correction = any(marker in normalized for marker in CORRECTION_MARKERS)

    if not explicit and not correction:
        return suggestions

    if "nao tem consciencia" in normalized or "limites ontologicos" in normalized:
        suggestions.append(
            {
                "type": "preference",
                "content": (
                    "Reginaldo prefere que Luzia não repita limites ontológicos "
                    "em toda resposta."
                ),
                "source": "user_explicit",
                "confidence": 0.95,
                "tags": ["luzia", "personalidade", "ontologia", "tom"],
            }
        )
    elif correction:
        suggestions.append(
            {
                "type": "correction",
                "content": f"Correção explícita de Reginaldo: {prompt.strip()}",
                "source": "correction",
                "confidence": 0.95,
                "tags": ["correcao", "luzia"],
            }
        )
    elif "prefiro que" in normalized or "quero que voce" in normalized:
        suggestions.append(
            {
                "type": "preference",
                "content": f"Preferência explícita de Reginaldo: {prompt.strip()}",
                "source": "user_explicit",
                "confidence": 0.9,
                "tags": ["preferencia", "reginaldo"],
            }
        )
    elif explicit:
        suggestions.append(
            {
                "type": "symbolic",
                "content": f"Memória explícita solicitada por Reginaldo: {prompt.strip()}",
                "source": "user_explicit",
                "confidence": 0.85,
                "tags": ["memoria", "luzia"],
            }
        )

    return suggestions


def save_inferred_memories(prompt: str) -> list[dict[str, Any]]:
    """Salva memorias inferidas somente quando as regras permitirem."""

    saved = []
    for suggestion in infer_memory_from_user_prompt(prompt):
        saved.append(
            add_memory(
                suggestion["type"],
                suggestion["content"],
                source=suggestion["source"],
                confidence=suggestion["confidence"],
                tags=suggestion["tags"],
            )
        )
    return saved


def build_memory_context(current_prompt: str, limit: int = 5) -> list[dict[str, Any]]:
    """Recupera memorias relevantes para o prompt atual."""

    ensure_memory_files()
    memories = search_memories(current_prompt, limit=limit)
    if memories:
        return memories

    creator = list_memories("creator")[:1]
    preferences = list_memories("preference")[: max(0, limit - len(creator))]
    return (creator + preferences)[:limit]
