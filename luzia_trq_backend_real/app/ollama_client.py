from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.config import settings
from app.vector import deterministic_embedding


class OllamaUnavailable(RuntimeError):
    pass


class OllamaGenerationTimeout(OllamaUnavailable):
    pass


def _timeout_message(timeout_s: float) -> str:
    return f"Tempo limite total de geracao excedido ({timeout_s:g} segundos)."


class OllamaClient:
    def __init__(self, base_url: str | None = None, timeout_s: float | None = None) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout_s = timeout_s or settings.request_timeout_s

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                return {"ok": True, "base_url": self.base_url, "data": response.json()}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "base_url": self.base_url, "error": str(exc)}

    async def generate(
        self,
        *,
        prompt: str,
        system: str,
        model: str | None = None,
        temperature: float = 0.35,
    ) -> dict[str, Any]:
        payload = {
            "model": model or settings.ollama_model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 8192,
            },
        }
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                elapsed = max(time.perf_counter() - started, 1e-6)
                text = data.get("response", "").strip()
                eval_count = data.get("eval_count") or len(text.split())
                return {
                    "text": text,
                    "source": "ollama",
                    "model": payload["model"],
                    "elapsed_s": round(elapsed, 4),
                    "tokens": int(eval_count),
                    "tps": round(float(eval_count) / elapsed, 4),
                    "raw": data,
                }
        except Exception as exc:  # noqa: BLE001
            elapsed = max(time.perf_counter() - started, 1e-6)
            if isinstance(exc, httpx.TimeoutException) or elapsed >= self.timeout_s:
                raise OllamaUnavailable(_timeout_message(self.timeout_s)) from exc
            if not settings.allow_fallback:
                raise OllamaUnavailable(str(exc)) from exc
            text = self._fallback_response(prompt)
            tokens = len(text.split())
            return {
                "text": text,
                "source": "fallback_local_deterministic",
                "model": payload["model"],
                "elapsed_s": round(elapsed, 4),
                "tokens": tokens,
                "tps": round(tokens / elapsed, 4),
                "raw": {"error": str(exc)},
            }

    async def generate_stream(
        self,
        *,
        prompt: str,
        system: str,
        model: str | None = None,
        temperature: float = 0.35,
    ):
        """Geracao em streaming.

        Produz eventos {"type": "token", "text": ...} conforme o Ollama emite,
        e um evento final {"type": "final", ...} com o texto completo e a
        telemetria (tokens, tps). Se o Ollama falhar, cai no mesmo fallback
        deterministico de generate(), emitido palavra a palavra para manter a
        experiencia de streaming.
        """

        payload = {
            "model": model or settings.ollama_model,
            "prompt": prompt,
            "system": system,
            "stream": True,
            "options": {"temperature": temperature, "num_ctx": 8192},
        }
        started = time.perf_counter()
        parts: list[str] = []
        eval_count = 0
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/api/generate", json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if time.perf_counter() - started >= self.timeout_s:
                            raise OllamaGenerationTimeout(_timeout_message(self.timeout_s))
                        if not line.strip():
                            continue
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            parts.append(chunk)
                            yield {"type": "token", "text": chunk}
                        if data.get("done"):
                            eval_count = data.get("eval_count") or len("".join(parts).split())
            elapsed = max(time.perf_counter() - started, 1e-6)
            text = "".join(parts).strip()
            tokens = int(eval_count) or len(text.split())
            yield {
                "type": "final",
                "text": text,
                "source": "ollama",
                "model": payload["model"],
                "elapsed_s": round(elapsed, 4),
                "tokens": tokens,
                "tps": round(tokens / elapsed, 4),
            }
            return
        except Exception as exc:  # noqa: BLE001
            partial = "".join(parts).strip()
            elapsed = max(time.perf_counter() - started, 1e-6)
            timeout_error = (
                isinstance(exc, (httpx.TimeoutException, OllamaGenerationTimeout))
                or elapsed >= self.timeout_s
            )
            if partial:
                # Ja emitiu tokens reais; finaliza com o que veio do Ollama.
                tokens = len(partial.split())
                yield {
                    "type": "final",
                    "text": partial,
                    "source": "ollama_timeout_partial" if timeout_error else "ollama_partial",
                    "model": payload["model"],
                    "elapsed_s": round(elapsed, 4),
                    "tokens": tokens,
                    "tps": round(tokens / elapsed, 4),
                    "error": str(exc),
                }
                return
            if timeout_error:
                raise OllamaUnavailable(_timeout_message(self.timeout_s)) from exc
            if not settings.allow_fallback:
                raise OllamaUnavailable(str(exc)) from exc

        # Fallback deterministico, emitido palavra a palavra.
        text = self._fallback_response(prompt)
        for word in text.split(" "):
            yield {"type": "token", "text": word + " "}
        elapsed = max(time.perf_counter() - started, 1e-6)
        tokens = len(text.split())
        yield {
            "type": "final",
            "text": text,
            "source": "fallback_local_deterministic",
            "model": payload["model"],
            "elapsed_s": round(elapsed, 4),
            "tokens": tokens,
            "tps": round(tokens / elapsed, 4),
        }

    async def embed(self, text: str, *, model: str | None = None) -> dict[str, Any]:
        model_name = model or settings.ollama_embed_model
        # API clássica do Ollama.
        payload = {"model": model_name, "prompt": text}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.post(f"{self.base_url}/api/embeddings", json=payload)
                response.raise_for_status()
                data = response.json()
                embedding = data.get("embedding")
                if isinstance(embedding, list) and embedding:
                    return {"embedding": [float(v) for v in embedding], "source": "ollama", "model": model_name}
        except Exception:
            pass

        # API nova, quando disponível.
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.post(f"{self.base_url}/api/embed", json={"model": model_name, "input": text})
                response.raise_for_status()
                data = response.json()
                embeddings = data.get("embeddings")
                if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
                    return {"embedding": [float(v) for v in embeddings[0]], "source": "ollama", "model": model_name}
        except Exception as exc:  # noqa: BLE001
            if not settings.allow_fallback:
                raise OllamaUnavailable(str(exc)) from exc

        return {"embedding": deterministic_embedding(text), "source": "fallback_hash", "model": "hash-256"}

    @staticmethod
    def _fallback_response(prompt: str) -> str:
        return (
            "Pipeline TRQ META executado em modo local determinístico porque o serviço Ollama não respondeu. "
            "A entrada foi tratada como estímulo semântico; a resposta foi co-registrada com memória vetorial, "
            "avaliada por métricas I, S, F, D e A, e preparada para decisão de expansão NQC. "
            "Para ativar resposta generativa real, abra o Ollama em localhost:11434 e instale o modelo configurado. "
            f"Estímulo analisado: {prompt[:500]}"
        )
