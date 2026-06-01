from __future__ import annotations

"""Testes simples da TRQ Persistent Memory Layer.

Roda sem Ollama e usa um diretorio temporario para nao poluir a memoria real.
"""

import tempfile
from pathlib import Path

import memory_store as store
from presence_prompt import build_memory_context_prompt


def configure_temp_memory(base: Path) -> None:
    """Redireciona os caminhos globais do memory_store para um temp dir."""

    store.MEMORY_DIR = base
    store.RAW_CONVERSATIONS_DIR = base / "raw_conversations"
    store.LONG_TERM_MEMORY_PATH = base / "long_term_memory.json"
    store.CREATOR_MEMORY_PATH = base / "creator_profile_memory.json"
    store.PREFERENCES_PATH = base / "luzia_preferences.json"
    store.CORRECTIONS_PATH = base / "corrections_log.json"
    store.SUMMARIES_PATH = base / "conversation_summaries.md"
    store.TYPE_TO_PATH = {
        "preference": store.PREFERENCES_PATH,
        "correction": store.CORRECTIONS_PATH,
        "creator": store.CREATOR_MEMORY_PATH,
        "project": store.LONG_TERM_MEMORY_PATH,
        "symbolic": store.LONG_TERM_MEMORY_PATH,
        "technical": store.LONG_TERM_MEMORY_PATH,
        "relationship": store.LONG_TERM_MEMORY_PATH,
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        configure_temp_memory(Path(temp_dir))
        store.ensure_memory_files()

        preference = store.add_preference(
            "Reginaldo prefere respostas com presença simbólica e sem frieza."
        )
        assert preference["type"] == "preference"
        assert preference["active"] is True

        found = store.search_memories("presença frieza")
        assert found
        assert found[0]["id"] == preference["id"]

        correction = store.add_correction(
            "responder frio",
            "responder com presença simbólica e clareza",
        )
        assert correction["type"] == "correction"

        context = store.build_memory_context("presença simbólica", limit=3)
        prompt = build_memory_context_prompt(context)
        assert "MEMÓRIAS RELEVANTES" in prompt
        assert "presença simbólica" in prompt

        assert store.deactivate_memory(preference["id"][:8]) is True
        active_ids = {memory["id"] for memory in store.list_memories()}
        assert preference["id"] not in active_ids

        print("memory_store tests OK")


if __name__ == "__main__":
    main()
