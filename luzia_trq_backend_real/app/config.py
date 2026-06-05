from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "sim", "on"}


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    db_path: Path = Path(os.getenv("LZ_DB_PATH", "./data/luzia_trq.sqlite3"))
    jsonl_path: Path = Path(os.getenv("LZ_JSONL_PATH", "./data/luzia_trq_runs.jsonl"))
    allow_fallback: bool = _env_bool("LZ_ALLOW_FALLBACK", True)
    request_timeout_s: float = float(os.getenv("OLLAMA_TIMEOUT", "600"))


settings = Settings()
