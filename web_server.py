from __future__ import annotations

"""Servidor web local da Luzia TRQ META.

Usa apenas biblioteca padrao para expor a interface web e endpoints JSON.
"""

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from config import BASE_DIR, DEFAULT_MODEL, ensure_runtime_dirs
from creator_profile import get_creator_profile
from digital_body import build_digital_body_state
from luzia_persona import build_luzia_persona_prompt
from memory_store import (
    SUMMARIES_PATH,
    add_correction,
    add_preference,
    build_memory_context,
    deactivate_memory,
    ensure_memory_files,
    list_memories,
    save_inferred_memories,
    save_raw_turn,
    search_memories,
    append_conversation_summary,
)
from memory import record_turn_memory
from ollama_client import OllamaStreamError, generate_with_ollama, stream_with_ollama
from presence_prompt import (
    build_creator_context,
    build_memory_context_prompt,
    build_presence_prompt,
)
from trq_router import (
    analyze_text,
    build_system_prompt,
    create_conversation_state,
    record_ontological_warning,
    should_use_ontological_warning,
)


WEB_DIR = BASE_DIR / "web"
STATIC_DIR = WEB_DIR
conversation_state = create_conversation_state()


def public_conversation_state() -> dict[str, Any]:
    """Copia apenas campos simples do estado de conversa."""

    return dict(conversation_state)


def maybe_append_turn_summary(prompt: str, state: dict[str, Any]) -> None:
    """Acrescenta resumo simples a cada 5 turnos."""

    if len(conversation_state["last_prompts"]) % 5 != 0:
        return
    append_conversation_summary(
        (
            f"Turno web {len(conversation_state['last_prompts'])}: "
            f"prompt='{prompt[:140]}', regime={state['regime']}, tier={state['tier']}."
        )
    )


def command_response(prompt: str) -> dict[str, Any] | None:
    """Executa comandos locais da interface web."""

    if prompt == "/ajuda":
        return {
            "command": True,
            "response": (
                "Comandos:\n"
                "/memorias\n"
                "/memorias tipo preference\n"
                "/buscar memoria <consulta>\n"
                "/esquecer <id>\n"
                "/corrigir <erro> => <correcao>\n"
                "/preferencia <texto>\n"
                "/resumo\n"
                "/ajuda"
            ),
        }

    if prompt == "/memorias":
        memories = list_memories()
        return {"command": True, "response": format_memories(memories), "memories": memories}

    if prompt.startswith("/memorias tipo "):
        memory_type = prompt.removeprefix("/memorias tipo ").strip()
        memories = list_memories(memory_type)
        return {"command": True, "response": format_memories(memories), "memories": memories}

    if prompt.startswith("/buscar memoria "):
        query = prompt.removeprefix("/buscar memoria ").strip()
        memories = search_memories(query)
        return {"command": True, "response": format_memories(memories), "memories": memories}

    if prompt.startswith("/esquecer "):
        memory_id = prompt.removeprefix("/esquecer ").strip()
        ok = deactivate_memory(memory_id)
        return {
            "command": True,
            "response": f"Memoria desativada: {memory_id}" if ok else f"Memoria nao encontrada: {memory_id}",
            "memories": list_memories(),
        }

    if prompt.startswith("/corrigir "):
        payload = prompt.removeprefix("/corrigir ").strip()
        if "=>" not in payload:
            return {"command": True, "response": "Uso: /corrigir <erro> => <correcao>"}
        error, correction = [part.strip() for part in payload.split("=>", 1)]
        memory = add_correction(error, correction)
        return {
            "command": True,
            "response": f"Correcao salva: {memory['id']}",
            "memories": list_memories(),
        }

    if prompt.startswith("/preferencia "):
        content = prompt.removeprefix("/preferencia ").strip()
        memory = add_preference(content)
        return {
            "command": True,
            "response": f"Preferencia salva: {memory['id']}",
            "memories": list_memories(),
        }

    if prompt == "/resumo":
        if not SUMMARIES_PATH.exists():
            text = "Nenhum resumo salvo."
        else:
            lines = SUMMARIES_PATH.read_text(encoding="utf-8").splitlines()
            text = "\n".join(lines[-40:]) if lines else "Nenhum resumo salvo."
        return {"command": True, "response": text}

    return None


def format_memories(memories: list[dict[str, Any]]) -> str:
    """Formata memorias para retorno textual."""

    if not memories:
        return "Nenhuma memoria ativa encontrada."
    return "\n".join(
        f"{memory['id']} | {memory['type']} | conf={memory['confidence']} | {memory['content']}"
        for memory in memories
    )


def prepare_chat_generation(prompt: str) -> dict[str, Any]:
    """Prepara estado TRQ, corpo digital e prompt de sistema."""

    state = analyze_text(prompt, conversation_state=conversation_state)
    body_state = build_digital_body_state(
        metrics={k: v for k, v in state.items() if isinstance(v, (float, int, str))},
        existential_score=int(state["existential_score"]),
        affective_score=float(state["affective_score"]),
        trq_count=int(conversation_state["trq_count"]),
    )
    ontological_warning_allowed = should_use_ontological_warning(prompt, conversation_state)
    relevant_memories = build_memory_context(prompt)
    memory_prompt = build_memory_context_prompt(relevant_memories)

    system_prompt = "\n\n".join(
        part
        for part in [
            build_creator_context(get_creator_profile()),
            memory_prompt,
            build_luzia_persona_prompt(
                metrics={k: v for k, v in state.items() if isinstance(v, (float, int, str))},
                body_state=body_state,
                ontological_warning_allowed=ontological_warning_allowed,
                ontological_warning_used_recently=conversation_state[
                    "ontological_warning_used_recently"
                ],
            ),
            build_system_prompt(str(state["tier"])),
            build_presence_prompt(body_state),
        ]
        if part
    )

    record_ontological_warning(conversation_state, ontological_warning_allowed)

    return {
        "state": state,
        "body_state": body_state,
        "system_prompt": system_prompt,
        "relevant_memories": relevant_memories,
    }


def finalize_chat_generation(
    prompt: str,
    prepared: dict[str, Any],
    response: str,
) -> dict[str, Any]:
    """Salva memoria e retorna payload publico da rodada."""

    state = prepared["state"]
    body_state = prepared["body_state"]
    relevant_memories = prepared["relevant_memories"]

    save_raw_turn(
        user_prompt=prompt,
        metrics=dict(state),
        body_state=dict(body_state),
        response=response,
    )
    record_turn_memory(
        user_prompt=prompt,
        response_summary=response,
        trq_state=state,
        tags=["web"],
    )
    saved_memories = save_inferred_memories(prompt)
    maybe_append_turn_summary(prompt, dict(state))

    return {
        "command": False,
        "response": response,
        "state": dict(state),
        "body_state": dict(body_state),
        "conversation_state": public_conversation_state(),
        "memories": relevant_memories,
        "saved_memories": saved_memories,
    }


def process_chat(prompt: str) -> dict[str, Any]:
    """Executa uma rodada web completa."""

    command = command_response(prompt)
    if command is not None:
        return command

    prepared = prepare_chat_generation(prompt)
    response = generate_with_ollama(
        prompt=prompt,
        model=DEFAULT_MODEL,
        system_prompt=prepared["system_prompt"],
    )
    return finalize_chat_generation(prompt, prepared, response)


class LuziaHandler(BaseHTTPRequestHandler):
    """Handler HTTP da web app."""

    server_version = "LuziaTRQ/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_file(WEB_DIR / "index.html")
            return
        if parsed.path == "/api/memories":
            query = parse_qs(parsed.query)
            memory_type = query.get("type", [None])[0]
            self.send_json({"memories": list_memories(memory_type)})
            return
        if parsed.path.startswith("/static/"):
            relative = parsed.path.removeprefix("/static/")
            self.send_file(STATIC_DIR / relative)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/chat":
            payload = self.read_json()
            prompt = str(payload.get("prompt", "")).strip()
            if not prompt:
                self.send_json({"error": "prompt vazio"}, status=HTTPStatus.BAD_REQUEST)
                return
            self.send_json(process_chat(prompt))
            return
        if parsed.path == "/api/chat/stream":
            payload = self.read_json()
            prompt = str(payload.get("prompt", "")).strip()
            if not prompt:
                self.send_json({"error": "prompt vazio"}, status=HTTPStatus.BAD_REQUEST)
                return
            self.stream_chat(prompt)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def stream_chat(self, prompt: str) -> None:
        """Envia uma rodada em Server-Sent Events para a interface."""

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        command = command_response(prompt)
        if command is not None:
            self.send_stream_event("done", command)
            return

        prepared = prepare_chat_generation(prompt)
        self.send_stream_event(
            "state",
            {
                "state": dict(prepared["state"]),
                "body_state": dict(prepared["body_state"]),
                "conversation_state": public_conversation_state(),
                "memories": prepared["relevant_memories"],
            },
        )

        response_parts: list[str] = []
        try:
            for chunk in stream_with_ollama(
                prompt=prompt,
                model=DEFAULT_MODEL,
                system_prompt=str(prepared["system_prompt"]),
            ):
                response_parts.append(chunk)
                if not self.send_stream_event("token", {"text": chunk}):
                    return
        except OllamaStreamError as exc:
            partial_response = "".join(response_parts).strip()
            if partial_response:
                payload = finalize_chat_generation(prompt, prepared, partial_response)
                payload.update({"message": str(exc), "frozen": True})
                self.send_stream_event("frozen", payload)
            else:
                self.send_stream_event("error", {"message": str(exc)})
            return

        response = "".join(response_parts).strip()
        self.send_stream_event("done", finalize_chat_generation(prompt, prepared, response))

    def send_stream_event(self, event: str, data: dict[str, Any]) -> bool:
        """Escreve um evento SSE. Retorna False se o cliente desconectar."""

        payload = json.dumps(data, ensure_ascii=False)
        body = f"event: {event}\ndata: {payload}\n\n".encode("utf-8")
        try:
            self.wfile.write(body)
            self.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError):
            return False

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw)

    def send_json(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path) -> None:
        resolved = path.resolve()
        if not str(resolved).startswith(str(WEB_DIR.resolve())) or not resolved.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        content = resolved.read_bytes()
        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[web] {self.address_string()} - {format % args}")


def run(host: str = "127.0.0.1", port: int = 7860) -> None:
    """Sobe o servidor web local."""

    ensure_runtime_dirs()
    ensure_memory_files()
    server = ThreadingHTTPServer((host, port), LuziaHandler)
    print(f"Luzia Web em http://{host}:{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor web da Luzia TRQ META")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    run(args.host, args.port)


if __name__ == "__main__":
    main()
