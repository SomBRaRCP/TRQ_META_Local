from __future__ import annotations

"""Simple JSONL memory log for TRQ conversation turns.

This layer records prompts, responses and selected TRQ metrics without changing
the routing, persona or existing preference/correction memory system.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from config import BASE_DIR
from trq_estimators import normalize_text


MEMORY_DIR = BASE_DIR / "memory"
MEMORY_LOG_PATH = MEMORY_DIR / "trq_memory.jsonl"
DEFAULT_TEXT_LIMIT = 4000


def now_iso() -> str:
    """Return the current UTC timestamp in ISO format."""

    return datetime.now(timezone.utc).isoformat()


def ensure_memory_log(path: Path | str = MEMORY_LOG_PATH) -> Path:
    """Create the memory directory and JSONL file if needed."""

    memory_path = Path(path)
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.touch(exist_ok=True)
    return memory_path


def _number(value: object) -> float:
    """Convert a metric to float while keeping invalid values neutral."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _state_value(trq_state: object, key: str, default: object = "") -> object:
    """Read a TRQ value from a mapping, object attribute or indexable state."""

    if isinstance(trq_state, Mapping):
        return trq_state.get(key, default)
    if hasattr(trq_state, key):
        return getattr(trq_state, key)
    try:
        return trq_state[key]  # type: ignore[index]
    except (KeyError, IndexError, TypeError, AttributeError):
        return default


def _tags(tags: list[str] | None) -> list[str]:
    """Normalize optional tags to non-empty strings."""

    if not tags:
        return []
    return [str(tag).strip() for tag in tags if str(tag).strip()]


def _truncate_text(value: object, max_chars: int) -> tuple[str, int, bool]:
    """Return text, original length and whether it had to be truncated."""

    text = str(value)
    original_length = len(text)
    if max_chars < 1:
        return "", original_length, original_length > 0
    if original_length <= max_chars:
        return text, original_length, False
    return text[:max_chars], original_length, True


def _warn_memory_failure(action: str, error: Exception) -> None:
    """Print a clear warning without interrupting the main application flow."""

    print(f"Aviso: falha ao {action} memoria TRQ: {error}")


def build_memory_record(
    user_prompt: str,
    response_summary: str,
    trq_state: object,
    tags: list[str] | None = None,
    timestamp: str | None = None,
    max_chars: int = DEFAULT_TEXT_LIMIT,
) -> dict[str, Any]:
    """Build the stable JSONL record for one TRQ turn."""

    prompt_text, prompt_original_length, prompt_truncated = _truncate_text(
        user_prompt,
        max_chars=max_chars,
    )
    response_text, response_original_length, response_truncated = _truncate_text(
        response_summary,
        max_chars=max_chars,
    )

    record: dict[str, Any] = {
        "timestamp": timestamp or now_iso(),
        "user_prompt": prompt_text,
        "response_summary": response_text,
        "regime": str(_state_value(trq_state, "regime")),
        "tier": str(_state_value(trq_state, "tier")),
        "I": _number(_state_value(trq_state, "I")),
        "S_norm": _number(_state_value(trq_state, "S_norm")),
        "F_flow_norm": _number(_state_value(trq_state, "F_flow_norm")),
        "M": _number(_state_value(trq_state, "M")),
        "C_llm": _number(_state_value(trq_state, "C_llm")),
        "tags": _tags(tags),
    }

    if prompt_truncated:
        record["user_prompt_chars_original"] = prompt_original_length
    if response_truncated:
        record["response_chars_original"] = response_original_length

    return record


def append_memory_record(
    record: Mapping[str, Any],
    path: Path | str = MEMORY_LOG_PATH,
) -> dict[str, Any] | bool:
    """Append a prebuilt record to the JSONL memory log."""

    try:
        memory_path = ensure_memory_log(path)
        stored = dict(record)
        with memory_path.open("a", encoding="utf-8") as memory_file:
            memory_file.write(json.dumps(stored, ensure_ascii=False) + "\n")
        return stored
    except OSError as error:
        _warn_memory_failure("gravar", error)
        return False


def record_turn_memory(
    user_prompt: str,
    response_summary: str,
    trq_state: object,
    tags: list[str] | None = None,
    path: Path | str = MEMORY_LOG_PATH,
    max_chars: int = DEFAULT_TEXT_LIMIT,
) -> dict[str, Any] | bool:
    """Create and persist one conversation memory record."""

    try:
        record = build_memory_record(
            user_prompt=user_prompt,
            response_summary=response_summary,
            trq_state=trq_state,
            tags=tags,
            max_chars=max_chars,
        )
        return append_memory_record(record, path=path)
    except Exception as error:
        _warn_memory_failure("preparar", error)
        return False


def iter_memory_records(path: Path | str = MEMORY_LOG_PATH) -> list[dict[str, Any]]:
    """Read all valid JSONL records in chronological order."""

    try:
        memory_path = ensure_memory_log(path)
    except OSError as error:
        _warn_memory_failure("abrir", error)
        return []

    records: list[dict[str, Any]] = []
    try:
        for line in memory_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                records.append(item)
    except OSError as error:
        _warn_memory_failure("ler", error)
    return records


def get_recent_records(limit: int = 10, path: Path | str = MEMORY_LOG_PATH) -> list[dict[str, Any]]:
    """Return the latest N memory records."""

    if limit <= 0:
        return []
    return iter_memory_records(path)[-limit:]


def search_memory_records(
    keyword: str,
    limit: int = 10,
    path: Path | str = MEMORY_LOG_PATH,
) -> list[dict[str, Any]]:
    """Search recent memory records by simple keyword overlap."""

    normalized_keyword = normalize_text(keyword)
    terms = {term for term in normalized_keyword.split() if len(term) >= 2}
    if not terms or limit <= 0:
        return []

    matches: list[dict[str, Any]] = []
    for record in reversed(iter_memory_records(path)):
        haystack = normalize_text(
            " ".join(
                [
                    str(record.get("user_prompt", "")),
                    str(record.get("response_summary", "")),
                    str(record.get("regime", "")),
                    str(record.get("tier", "")),
                    " ".join(str(tag) for tag in record.get("tags", [])),
                ]
            )
        )
        if any(term in haystack for term in terms):
            matches.append(record)
        if len(matches) >= limit:
            break
    return matches
