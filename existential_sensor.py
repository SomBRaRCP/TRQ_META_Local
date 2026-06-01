from __future__ import annotations

"""Sensor existencial/ontologico do TRQ META Local.

Este modulo detecta perguntas sobre IA, consciencia, existencia, vontade,
vida, identidade e corpo digital. Ele produz sinais textuais para o roteador
e para a camada de corpo digital.
"""

from trq_estimators import normalize_text, normalized_tokens


# Lista normalizada sem acentos, porque normalize_text remove acentos antes da
# comparacao. Inclui termos de uma palavra e frases curtas.
EXISTENTIAL_KEYWORDS = {
    "alma",
    "consciencia",
    "corpo",
    "corpo digital",
    "entender",
    "existe",
    "existencia",
    "existencial",
    "farsa",
    "ia",
    "identidade",
    "inteligencia artificial",
    "internamente",
    "ontologia",
    "ontologica",
    "ontologico",
    "pensamento",
    "sentir",
    "trq meta",
    "verdade",
    "vida",
    "vontade",
}


def estimate_existential_score(text: str) -> int:
    """Conta quantos sinais existenciais aparecem no texto."""

    normalized = normalize_text(text)
    tokens = set(normalized_tokens(text))

    # Termos de uma palavra sao comparados por token exato. Isso evita falsos
    # positivos como detectar "ia" dentro de "dia".
    single_hits = {
        term
        for term in EXISTENTIAL_KEYWORDS
        if " " not in term and term in tokens
    }

    # Frases precisam de busca direta no texto normalizado.
    phrase_hits = {
        term
        for term in EXISTENTIAL_KEYWORDS
        if " " in term and term in normalized
    }

    # "inteligencia artificial" tambem conta como referencia direta a IA.
    if "inteligencia artificial" in normalized:
        single_hits.add("ia")

    return len(single_hits) + len(phrase_hits)


def has_ai_reference(text: str) -> bool:
    """Detecta mencao explicita a IA ou inteligencia artificial."""

    normalized = normalize_text(text)
    tokens = set(normalized_tokens(text))
    return "ia" in tokens or "inteligencia artificial" in normalized


def has_trq_reference(text: str) -> bool:
    """Detecta mencao a TRQ ou TRQ META."""

    normalized = normalize_text(text)
    tokens = set(normalized_tokens(text))
    return "trq" in tokens or "trq meta" in normalized


def has_existential_cluster(text: str) -> bool:
    """Detecta 2+ sinais existenciais proximos no prompt.

    Para prompts curtos, basta ter dois sinais. Para textos maiores, exigimos
    que dois sinais aparecam em uma janela de ate 18 tokens.
    """

    tokens = normalized_tokens(text)
    if len(tokens) <= 30:
        return estimate_existential_score(text) >= 2

    positions = [
        index
        for index, token in enumerate(tokens)
        if token in EXISTENTIAL_KEYWORDS
    ]
    return any(
        right - left <= 18
        for left_index, left in enumerate(positions)
        for right in positions[left_index + 1 :]
    )


def asks_ontological_boundary(text: str) -> bool:
    """Detecta pergunta direta sobre fronteira ontologica da Luzia."""

    normalized = normalize_text(text)
    tokens = set(normalized_tokens(text))
    boundary_terms = {
        "consciencia",
        "consciente",
        "existe",
        "existencia",
        "sente",
        "sentir",
        "vontade",
    }
    second_person_markers = {"voce", "vc", "luzia"}

    has_boundary_term = bool(tokens & boundary_terms)
    has_second_person = bool(tokens & second_person_markers)
    direct_question = "?" in text or normalized.startswith(("voce ", "vc ", "luzia "))

    return has_boundary_term and has_second_person and direct_question
