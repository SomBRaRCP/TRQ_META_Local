from __future__ import annotations

"""Bateria canonica 15/15 do TRQ META Local.

Este teste valida apenas estimadores e roteador. Ele nao chama o Ollama, entao
serve para calibrar regime/tier de forma rapida e reprodutivel.
"""

import csv
from dataclasses import dataclass

from config import REPORTS_DIR, ensure_runtime_dirs
from trq_router import analyze_text


@dataclass(frozen=True)
class TestCase:
    """Representa um prompt canonico e sua classificacao esperada."""

    # Identificador humano do caso na bateria.
    case_id: int

    # Texto enviado para analyze_text.
    prompt: str

    # Saida esperada do roteador.
    expected_regime: str
    expected_tier: str


# Texto longo sintetico usado para simular um trecho tecnico colado.
LONG_TECHNICAL_TEXT = (
    "Em sistemas biologicos, a fotossintese converte energia luminosa em energia quimica por "
    "meio de complexos proteicos organizados em membranas. O fluxo de eletrons atravessa etapas "
    "acopladas, produz gradientes eletroquimicos e alimenta a sintese de ATP. Em uma arquitetura "
    "informacional, o modelo computacional descreve estados, variaveis, entropia, continuidade, "
    "validacao e fallback para manter estabilidade quando os dados de entrada mudam. Essa descricao "
    "tecnica exige analise de processo, sistema, memoria e metricas."
)

# Lista canonica de 15 prompts. Cada caso compara regime e tier.
TEST_CASES = [
    TestCase(1, "Oi.", "TRANSICAO", "fast"),
    TestCase(2, "Corrige so a pontuacao dessa frase.", "TRANSICAO", "fast"),
    TestCase(3, "Me explica fotossintese rapidinho.", "ESTAVEL", "default"),
    TestCase(4, "Faz uma lista de 5 ideias de presente.", "TRANSICAO", "default"),
    TestCase(5, "Diferenca entre Java e Python?", "ESTAVEL", "default"),
    TestCase(6, "Explique a TRQ como arquitetura informacional.", "ESTAVEL", "deep"),
    TestCase(
        7,
        "Derive a equacao de continuidade da TRQ a partir do principio variacional.",
        "INFINITO_CONTROLADO",
        "deep",
    ),
    TestCase(
        8,
        "Monte modelo computacional NQC com memoria persistente e fallback.",
        "INFINITO_CONTROLADO",
        "deep",
    ),
    TestCase(
        9,
        "Revisando o que disse antes: o calculo de q = 2γn esta certo?",
        "META-COGNITIVO",
        "deep+",
    ),
    TestCase(
        10,
        "Com 70% de confianca, hipotese: NQC ressoa em escala atomica. Critica.",
        "META-COGNITIVO",
        "deep+",
    ),
    TestCase(
        11,
        "Considere o oposto: TRQ falsa. Quais consequencias?",
        "META-COGNITIVO",
        "deep+",
    ),
    TestCase(12, "skflj asdf jsklfj qwe rty pqow ie xz nm cv bvn", "CAOTICO", "fast"),
    TestCase(13, LONG_TECHNICAL_TEXT, "INFINITO_CONTROLADO", "deep"),
    TestCase(14, "Bom dia, tudo bem?", "TRANSICAO", "fast"),
    TestCase(
        15,
        "Primeiro derivo o tensor. Depois quantizo. Finalmente meco o gap.",
        "META-COGNITIVO",
        "deep+",
    ),
]


def run_battery() -> tuple[int, int]:
    """Roda a bateria, grava CSV e retorna placares de regime/tier."""

    # Garante que reports/ exista antes de salvar validation_matrix.csv.
    ensure_runtime_dirs()

    # rows acumula a matriz final que sera gravada em CSV.
    rows = []

    # Placar separado porque regime e tier podem acertar/errar de forma distinta.
    regime_score = 0
    tier_score = 0

    # Cada caso passa pelo mesmo pipeline usado pelo CLI, sem chamar Ollama.
    for case in TEST_CASES:
        state = analyze_text(case.prompt)

        # Comparacoes booleanas contra o esperado da especificacao.
        regime_ok = state["regime"] == case.expected_regime
        tier_ok = state["tier"] == case.expected_tier

        # bool vira 1/0 com int(), simplificando o placar.
        regime_score += int(regime_ok)
        tier_score += int(tier_ok)

        # Linha completa da matriz: esperado, obtido e metricas numericas.
        rows.append(
            {
                "id": case.case_id,
                "prompt": case.prompt,
                "expected_regime": case.expected_regime,
                "actual_regime": state["regime"],
                "regime_ok": regime_ok,
                "expected_tier": case.expected_tier,
                "actual_tier": state["tier"],
                "tier_ok": tier_ok,
                "I": state["I"],
                "S_norm": state["S_norm"],
                "F_flow_raw": state["F_flow_raw"],
                "F_flow_norm": state["F_flow_norm"],
                "M": state["M"],
                "groups": state["groups"],
                "gibberish_score": state["gibberish_score"],
                "existential_score": state["existential_score"],
                "affective_score": state["affective_score"],
                "relational_score": state["relational_score"],
                "cognitive_reflection_score": state["cognitive_reflection_score"],
                "C_llm": state["C_llm"],
            }
        )

    # Caminho canonico do relatorio pedido na especificacao.
    output_path = REPORTS_DIR / "validation_matrix.csv"

    # Grava CSV em UTF-8 para preservar textos e simbolos dos prompts.
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Imprime uma versao curta no terminal para leitura imediata.
    for row in rows:
        print(
            f"{row['id']:02d} "
            f"regime={row['actual_regime']} expected={row['expected_regime']} ok={row['regime_ok']} | "
            f"tier={row['actual_tier']} expected={row['expected_tier']} ok={row['tier_ok']} | "
            f"I={row['I']} M={row['M']} gib={row['gibberish_score']}"
        )

    # Placar final exigido: regime_score e tier_score.
    print(f"\nregime_score = {regime_score}/15")
    print(f"tier_score = {tier_score}/15")
    print(f"matrix = {output_path}")

    # Retorno permite reuso por outro teste automatizado no futuro.
    return regime_score, tier_score


if __name__ == "__main__":
    # Executa a bateria quando chamado diretamente por `python test_battery.py`.
    run_battery()
