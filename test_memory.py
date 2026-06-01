from __future__ import annotations

"""Tests for the simple TRQ JSONL memory layer.

This script uses a temporary JSONL file and never writes to the real
memory/trq_memory.jsonl file.
"""

import tempfile
from pathlib import Path

from memory import (
    MEMORY_LOG_PATH,
    get_recent_records,
    record_turn_memory,
    search_memory_records,
)


class ObjectState:
    regime = "META-COGNITIVO"
    tier = "deep+"
    I = 0.77
    S_norm = 0.21
    F_flow_norm = 0.68
    M = 0.49
    C_llm = 0.88


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        test_path = Path(temp_dir) / "trq_memory_test.jsonl"

        created = record_turn_memory(
            user_prompt="Prompt com memória, coração e acentuação.",
            response_summary="Resposta preserva acentos: consciência, presença, ação.",
            trq_state=ObjectState(),
            tags=["teste", "acentuação"],
            path=test_path,
        )
        assert created is not False
        assert test_path.exists()

        recent = get_recent_records(1, path=test_path)
        assert len(recent) == 1
        assert recent[0]["regime"] == "META-COGNITIVO"
        assert recent[0]["tier"] == "deep+"
        assert recent[0]["I"] == 0.77

        found = search_memory_records("coração", path=test_path)
        assert len(found) == 1
        assert found[0]["user_prompt"].startswith("Prompt com memória")

        raw = test_path.read_text(encoding="utf-8")
        assert "memória" in raw
        assert "\\u00f3" not in raw

        long_response = "x" * 80
        truncated = record_turn_memory(
            user_prompt="y" * 50,
            response_summary=long_response,
            trq_state={
                "regime": "ESTAVEL",
                "tier": "default",
                "I": 0.55,
                "S_norm": 0.2,
                "F_flow_norm": 0.3,
                "M": 0.1,
                "C_llm": 0.4,
            },
            tags=["truncamento"],
            path=test_path,
            max_chars=20,
        )
        assert truncated is not False

        latest = get_recent_records(1, path=test_path)[0]
        assert len(latest["user_prompt"]) == 20
        assert len(latest["response_summary"]) == 20
        assert latest["user_prompt_chars_original"] == 50
        assert latest["response_chars_original"] == 80

        assert test_path != MEMORY_LOG_PATH
        assert MEMORY_LOG_PATH.name == "trq_memory.jsonl"

    print("test_memory OK")


if __name__ == "__main__":
    main()
