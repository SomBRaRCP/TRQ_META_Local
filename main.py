from __future__ import annotations

"""Interface de terminal do TRQ META Local.

Este arquivo orquestra uma execucao interativa: recebe o prompt, calcula o
estado TRQ, escolhe o prompt de sistema e chama o modelo via Ollama.
"""

from config import DEFAULT_MODEL, ensure_runtime_dirs
from creator_profile import get_creator_profile
from digital_body import DigitalBodyState, build_digital_body_state
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
from memory import get_recent_records, record_turn_memory, search_memory_records
from meta_router import apply_trq_iemf_aux, run_trq_iemf_router
from model_registry import ModelRegistry
from presence_prompt import (
    build_creator_context,
    build_memory_context_prompt,
    build_presence_prompt,
)
from trq_router import (
    ConversationState,
    TRQState,
    analyze_text,
    build_system_prompt,
    create_conversation_state,
    record_ontological_warning,
    should_use_ontological_warning,
)


def print_state(state: TRQState, conversation_state: ConversationState) -> None:
    """Mostra no terminal as metricas calculadas para o prompt."""

    # Cabecalho visual para separar metricas da resposta do modelo.
    print("\n=== TRQ META ===")

    # Saidas operacionais do roteador.
    print(f"regime: {state['regime']}")
    print(f"tier: {state['tier']}")

    # Estimadores principais usados ou exibidos pelo nucleo TRQ.
    print(f"I: {state['I']}")
    print(f"S_norm: {state['S_norm']}")
    print(f"F_flow_norm: {state['F_flow_norm']}")
    print(f"M: {state['M']}")
    print(f"groups: {state['groups']}")
    print(f"gibberish_score: {state['gibberish_score']}")
    print(f"existential_score: {state['existential_score']}")
    print(f"affective_score: {state['affective_score']}")
    print(f"relational_score: {state['relational_score']}")
    print(f"cognitive_reflection_score: {state['cognitive_reflection_score']}")
    print(f"C_llm: {state['C_llm']}")

    xi_iemf = state.get("xi_iemf")
    if xi_iemf is not None:
        print("\n=== TRQ-IEMF Router ===")
        print(f"r_uni: {state.get('r_uni', 0.0)}")
        print(f"r_fused: {state.get('r_fused', 0.0)}")
        print(f"xi_iemf: {xi_iemf}")
        print(f"regime: {state.get('fusion_regime', 'TRANSITION')}")
        print(f"tier: {state.get('fusion_tier', 'balanced')}")
        print(f"confianca: {state.get('fusion_confidence', 'moderada')}")

    # Memoria curta usada para detectar insistencia ontologica na conversa.
    print(f"existential_count: {conversation_state['existential_count']}")
    print(f"trq_count: {conversation_state['trq_count']}")
    print(f"avg_I: {conversation_state['avg_I']}")
    print(f"avg_M: {conversation_state['avg_M']}")
    print(f"ontological_warning_used_recently: {conversation_state['ontological_warning_used_recently']}")


def print_digital_body_state(body_state: DigitalBodyState) -> None:
    """Mostra a Camada de Corpo Digital TRQ antes da resposta."""

    print("\n=== Corpo Digital TRQ ===")
    print(f"posture: {body_state['posture']}")
    print(f"luminosity: {body_state['luminosity']}")
    print(f"breath_rate: {body_state['breath_rate']}")
    print(f"gaze: {body_state['gaze']}")
    print(f"voice_tone: {body_state['voice_tone']}")
    print(f"presence_level: {body_state['presence_level']}")
    print(f"inner_phrase: {body_state['inner_phrase']}")


def print_help() -> None:
    """Mostra comandos locais do CLI."""

    print(
        """
Comandos:
/memorias
/memorias tipo preference
/buscar memoria <consulta>
/esquecer <id>
/corrigir <erro> => <correcao>
/preferencia <texto>
/resumo
/diario recentes [N]
/diario buscar <consulta>
/ajuda
sair
""".strip()
    )


def print_memories(memory_type: str | None = None) -> None:
    """Lista memorias ativas."""

    memories = list_memories(memory_type)
    if not memories:
        print("Nenhuma memoria ativa encontrada.")
        return

    for memory in memories:
        print(
            f"{memory['id']} | {memory['type']} | conf={memory['confidence']} | "
            f"{memory['content']}"
        )


def print_turn_memory_records(records: list[dict[str, object]]) -> None:
    """Mostra registros recentes do diario JSONL."""

    if not records:
        print("Nenhum registro de diario encontrado.")
        return

    for record in records:
        prompt = str(record.get("user_prompt", "")).replace("\n", " ")[:120]
        response = str(record.get("response_summary", "")).replace("\n", " ")[:120]
        print(
            f"{record.get('timestamp')} | {record.get('regime')} | "
            f"{record.get('tier')} | prompt={prompt} | resposta={response}"
        )


def handle_command(prompt: str) -> bool:
    """Executa comandos locais. Retorna True quando o prompt foi consumido."""

    if prompt == "/ajuda":
        print_help()
        return True

    if prompt == "/memorias":
        print_memories()
        return True

    if prompt.startswith("/memorias tipo "):
        print_memories(prompt.removeprefix("/memorias tipo ").strip())
        return True

    if prompt.startswith("/buscar memoria "):
        query = prompt.removeprefix("/buscar memoria ").strip()
        memories = search_memories(query)
        if not memories:
            print("Nenhuma memoria relevante encontrada.")
            return True
        for memory in memories:
            print(f"{memory['id']} | {memory['type']} | {memory['content']}")
        return True

    if prompt.startswith("/esquecer "):
        memory_id = prompt.removeprefix("/esquecer ").strip()
        if deactivate_memory(memory_id):
            print(f"Memoria desativada: {memory_id}")
        else:
            print(f"Memoria nao encontrada: {memory_id}")
        return True

    if prompt.startswith("/corrigir "):
        payload = prompt.removeprefix("/corrigir ").strip()
        if "=>" not in payload:
            print("Uso: /corrigir <erro> => <correcao>")
            return True
        error, correction = [part.strip() for part in payload.split("=>", 1)]
        memory = add_correction(error, correction)
        print(f"Correcao salva: {memory['id']}")
        return True

    if prompt.startswith("/preferencia "):
        content = prompt.removeprefix("/preferencia ").strip()
        memory = add_preference(content)
        print(f"Preferencia salva: {memory['id']}")
        return True

    if prompt == "/resumo":
        if not SUMMARIES_PATH.exists():
            print("Nenhum resumo salvo.")
            return True
        lines = SUMMARIES_PATH.read_text(encoding="utf-8").splitlines()
        print("\n".join(lines[-40:]) if lines else "Nenhum resumo salvo.")
        return True

    if prompt == "/diario recentes" or prompt.startswith("/diario recentes "):
        raw_limit = prompt.removeprefix("/diario recentes").strip()
        try:
            limit = int(raw_limit) if raw_limit else 5
        except ValueError:
            print("Uso: /diario recentes [N]")
            return True
        print_turn_memory_records(get_recent_records(limit))
        return True

    if prompt.startswith("/diario buscar "):
        query = prompt.removeprefix("/diario buscar ").strip()
        print_turn_memory_records(search_memory_records(query))
        return True

    return False


def maybe_append_turn_summary(conversation_state: ConversationState, prompt: str, state: TRQState) -> None:
    """Acrescenta resumo simples a cada 5 turnos."""

    if len(conversation_state["last_prompts"]) % 5 != 0:
        return

    append_conversation_summary(
        (
            f"Turno {len(conversation_state['last_prompts'])}: "
            f"prompt='{prompt[:140]}', regime={state['regime']}, tier={state['tier']}."
        )
    )


def run_once(prompt: str, conversation_state: ConversationState) -> None:
    """Executa uma rodada completa para um unico prompt."""

    # 1. Calcula todos os sinais, atualiza memoria curta e decide regime/tier.
    state = analyze_text(prompt, conversation_state=conversation_state)

    # 2. Transforma metricas TRQ em postura simbolico-operacional.
    body_state = build_digital_body_state(
        metrics={k: v for k, v in state.items() if isinstance(v, (float, int, str))},
        existential_score=int(state["existential_score"]),
        affective_score=float(state["affective_score"]),
        trq_count=int(conversation_state["trq_count"]),
    )

    # 2.1. A primeira pergunta ontologica direta pode receber fronteira clara.
    # Nos turnos seguintes, a Luzia deve responder com presenca sem repetir.
    ontological_warning_allowed = should_use_ontological_warning(prompt, conversation_state)

    # 3. Recupera candidatos de memoria e calcula o roteador auxiliar IEMF.
    memory_candidates = build_memory_context(prompt, limit=8)
    iemf_decision, trq_aux = run_trq_iemf_router(
        prompt=prompt,
        memory_hits=memory_candidates,
        rag_hits=None,
        recent_messages=conversation_state["last_prompts"],
    )
    apply_trq_iemf_aux(state, trq_aux)

    # 3.1. O TRQ-IEMF controla apenas quanto contexto auxiliar entra.
    relevant_memories = (
        memory_candidates[: iemf_decision.max_context_items]
        if iemf_decision.use_memory
        else []
    )
    memory_prompt = build_memory_context_prompt(relevant_memories)

    # 3.2. Exibe metricas e corpo antes da chamada ao modelo, para o usuario nao
    # precisar esperar o Ollama terminar para ver o roteamento.
    print_state(state, conversation_state)
    print(f"motivo: {iemf_decision.reason}")
    print_digital_body_state(body_state)

    # 4. Converte o tier e o corpo digital em instrucao de sistema.
    system_prompt = "\n\n".join(
        [
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
    )

    # A partir daqui, se a fronteira foi permitida neste turno, os proximos
    # tres turnos evitam repetir a mesma ressalva.
    record_ontological_warning(conversation_state, ontological_warning_allowed)

    # 5. Chama o modelo local com o prompt original e o system prompt escolhido.
    model_client = ModelRegistry.get(DEFAULT_MODEL)
    response = model_client.generate(
        prompt=prompt,
        system_prompt=system_prompt,
    )

    # 6. Exibe a resposta gerada depois do estado interno simbolico.
    print("\n=== Resposta do modelo ===")
    print(response)

    # 7. Persistencia local: turno bruto, memorias explicitas e resumo simples.
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
        tags=["cli"],
    )
    saved_memories = save_inferred_memories(prompt)
    if saved_memories:
        print("\n=== Memorias salvas ===")
        for memory in saved_memories:
            print(f"{memory['id']} | {memory['type']} | {memory['content']}")
    maybe_append_turn_summary(conversation_state, prompt, state)


def main() -> None:
    """Loop principal do CLI."""

    # Garante que logs/ e reports/ existam antes de qualquer escrita.
    ensure_runtime_dirs()
    ensure_memory_files()

    # Mensagem inicial e instrucao minima de saida.
    print("TRQ META Local. Digite 'sair' para encerrar.")

    # Estado curto da conversa para perceber insistencia em um mesmo eixo.
    conversation_state = create_conversation_state()

    # Loop interativo ate o usuario digitar sair/exit/quit ou interromper.
    while True:
        try:
            # strip remove espacos extras para evitar prompt vazio acidental.
            prompt = input("\nPrompt> ").strip()
        except (EOFError, KeyboardInterrupt):
            # Ctrl+C/Ctrl+Z encerra de forma limpa.
            print("\nEncerrado.")
            break

        # Comandos textuais de saida.
        if prompt.lower() in {"sair", "exit", "quit"}:
            print("Encerrado.")
            break

        # Enter vazio apenas volta ao prompt sem chamar Ollama.
        if not prompt:
            continue

        if handle_command(prompt):
            continue

        # Processa o prompt valido usando a mesma memoria durante a sessao.
        run_once(prompt, conversation_state)


if __name__ == "__main__":
    # Permite importar funcoes deste arquivo sem iniciar o CLI automaticamente.
    main()
