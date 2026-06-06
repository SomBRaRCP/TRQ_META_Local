from __future__ import annotations

"""Shared model client registry.

The local Ollama runtime owns the actual model loading. This registry only
keeps one lightweight client wrapper per model name inside this Python process,
so TRQ META layers do not create competing client abstractions.
"""

from dataclasses import dataclass
from collections.abc import Iterator

from config import DEFAULT_MODEL, DEFAULT_NUM_CTX, DEFAULT_TEMPERATURE
from ollama_client import generate_with_ollama, stream_with_ollama


@dataclass(frozen=True)
class SharedOllamaClient:
    model_name: str

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = DEFAULT_TEMPERATURE,
        num_ctx: int = DEFAULT_NUM_CTX,
    ) -> str:
        return generate_with_ollama(
            prompt=prompt,
            model=self.model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            num_ctx=num_ctx,
        )

    def stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = DEFAULT_TEMPERATURE,
        num_ctx: int = DEFAULT_NUM_CTX,
    ) -> Iterator[str]:
        return stream_with_ollama(
            prompt=prompt,
            model=self.model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            num_ctx=num_ctx,
        )


class ModelRegistry:
    _clients: dict[str, SharedOllamaClient] = {}

    @classmethod
    def get(cls, model_name: str = DEFAULT_MODEL) -> SharedOllamaClient:
        if model_name not in cls._clients:
            cls._clients[model_name] = SharedOllamaClient(model_name=model_name)
        return cls._clients[model_name]
