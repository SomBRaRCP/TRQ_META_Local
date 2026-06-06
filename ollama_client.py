from __future__ import annotations

"""Cliente HTTP para a API local do Ollama.

Este modulo isola a chamada externa ao modelo. O resto do projeto pode testar
estimadores e roteamento sem depender de rede, GPU ou servidor Ollama ativo.
"""

import logging
import math
import json
import time
import socket
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

from config import (
    DEFAULT_GPU_BOOST_PERCENT,
    DEFAULT_MODEL,
    DEFAULT_NUM_CTX,
    DEFAULT_NUM_GPU,
    DEFAULT_NUM_GPU_MAX,
    DEFAULT_NUM_THREAD,
    DEFAULT_TEMPERATURE,
    LOG_FILE,
    OLLAMA_ENDPOINT,
    OLLAMA_TIMEOUT_SECONDS,
    ensure_runtime_dirs,
)


# Cria pastas de log/relatorio antes de configurar o arquivo de log.
ensure_runtime_dirs()

# Logging basico em arquivo local. Erros do Ollama ficam registrados para
# diagnostico sem quebrar o fluxo interativo do terminal.
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

# Logger especifico deste modulo.
logger = logging.getLogger(__name__)


class OllamaStreamError(RuntimeError):
    """Erro tratavel durante geracao em streaming."""


def _timeout_message() -> str:
    return (
        "Erro: a chamada ao Ollama excedeu o tempo limite total de "
        f"{OLLAMA_TIMEOUT_SECONDS} segundos."
    )


def _ollama_request(payload: dict[str, Any]) -> urllib.request.Request:
    body = json.dumps(payload).encode("utf-8")
    return urllib.request.Request(
        OLLAMA_ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )


def _boosted_num_gpu(raw_num_gpu: str) -> int:
    """Return num_gpu after the configured CUDA offload boost.

    Ollama treats num_gpu as the number of model layers to offload to GPU, not
    as a direct GPU utilization percentage. A 50% boost means 20 layers become
    30 layers. TRQ_NUM_GPU_MAX can cap the result for low-VRAM cards.
    """

    base_num_gpu = int(raw_num_gpu)
    if DEFAULT_GPU_BOOST_PERCENT <= 0:
        boosted = base_num_gpu
    else:
        boosted = math.ceil(base_num_gpu * (1 + DEFAULT_GPU_BOOST_PERCENT / 100))

    if DEFAULT_NUM_GPU_MAX:
        boosted = min(boosted, int(DEFAULT_NUM_GPU_MAX))

    return max(0, boosted)


def _runtime_options(temperature: float, num_ctx: int) -> dict[str, Any]:
    """Monta o bloco `options` esperado pelo endpoint /api/generate."""

    # Parametros sempre enviados.
    options: dict[str, Any] = {
        "temperature": temperature,
        "num_ctx": num_ctx,
    }

    # num_gpu e num_thread sao opcionais porque dependem do hardware local.
    if DEFAULT_NUM_GPU:
        options["num_gpu"] = _boosted_num_gpu(DEFAULT_NUM_GPU)
    if DEFAULT_NUM_THREAD:
        options["num_thread"] = int(DEFAULT_NUM_THREAD)

    # O dicionario pronto entra diretamente no payload HTTP.
    return options


def generate_with_ollama(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system_prompt: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    num_ctx: int = DEFAULT_NUM_CTX,
) -> str:
    """Chama o Ollama local e devolve apenas o texto gerado.

    Em caso de erro, a funcao retorna uma mensagem amigavel em vez de levantar
    excecao. Isso mantem o CLI simples e deixa o erro registrado em log.
    """

    # Payload minimo para geracao nao-streaming.
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": _runtime_options(temperature=temperature, num_ctx=num_ctx),
    }

    # O prompt de sistema muda conforme o tier calculado pelo roteador.
    if system_prompt:
        payload["system"] = system_prompt

    try:
        # Timeout padrao: 600 segundos, pois modelos grandes podem demorar.
        with urllib.request.urlopen(
            _ollama_request(payload),
            timeout=OLLAMA_TIMEOUT_SECONDS,
        ) as response:
            # Ollama retorna JSON com a chave "response" quando stream=false.
            data = json.loads(response.read().decode("utf-8"))
        return str(data.get("response", "")).strip()

    except urllib.error.HTTPError as exc:
        message = f"Erro HTTP {exc.code} ao chamar o Ollama: {exc.reason}"
        logger.exception(message)
        return message

    except urllib.error.URLError:
        # Servidor desligado, porta errada ou endpoint inacessivel.
        message = (
            "Erro: nao consegui conectar ao Ollama em "
            f"{OLLAMA_ENDPOINT}. Verifique se `ollama serve` esta rodando."
        )
        logger.exception(message)
        return message

    except (TimeoutError, socket.timeout):
        # A requisicao passou do limite configurado.
        message = "Erro: a chamada ao Ollama excedeu o tempo limite."
        logger.exception(message)
        return message

    except OSError as exc:
        # Erros HTTP, DNS, conexao abortada e outros problemas de rede.
        message = f"Erro ao chamar o Ollama: {exc}"
        logger.exception(message)
        return message

    except ValueError:
        # response.json() falhou: o servidor retornou algo que nao e JSON.
        message = "Erro: o Ollama retornou uma resposta JSON invalida."
        logger.exception(message)
        return message


def stream_with_ollama(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system_prompt: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    num_ctx: int = DEFAULT_NUM_CTX,
) -> Iterator[str]:
    """Chama o Ollama em streaming e rende os fragmentos de texto.

    Diferente de generate_with_ollama, esta funcao deixa excecoes trataveis
    chegarem ao servidor web para que a interface mantenha a resposta parcial
    congelada quando ocorrer timeout ou queda de conexao.
    """

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": _runtime_options(temperature=temperature, num_ctx=num_ctx),
    }
    if system_prompt:
        payload["system"] = system_prompt

    started = time.monotonic()

    try:
        with urllib.request.urlopen(
            _ollama_request(payload),
            timeout=OLLAMA_TIMEOUT_SECONDS,
        ) as response:
            for raw_line in response:
                if time.monotonic() - started >= OLLAMA_TIMEOUT_SECONDS:
                    message = _timeout_message()
                    logger.error(message)
                    raise OllamaStreamError(message)

                if not raw_line:
                    continue
                line = raw_line.decode("utf-8").strip()
                try:
                    data = json.loads(line)
                except ValueError:
                    logger.warning("Linha invalida no streaming do Ollama: %r", line)
                    continue

                chunk = data.get("response")
                if chunk:
                    yield str(chunk)
                if data.get("done"):
                    break

    except urllib.error.HTTPError as exc:
        message = f"Erro HTTP {exc.code} ao chamar o Ollama: {exc.reason}"
        logger.exception(message)
        raise OllamaStreamError(message) from exc

    except urllib.error.URLError as exc:
        message = (
            "Erro: nao consegui conectar ao Ollama em "
            f"{OLLAMA_ENDPOINT}. Verifique se `ollama serve` esta rodando."
        )
        logger.exception(message)
        raise OllamaStreamError(message) from exc

    except (TimeoutError, socket.timeout) as exc:
        message = "Erro: a chamada ao Ollama excedeu o tempo limite."
        logger.exception(message)
        raise OllamaStreamError(message) from exc

    except OSError as exc:
        message = f"Erro ao chamar o Ollama: {exc}"
        logger.exception(message)
        raise OllamaStreamError(message) from exc
