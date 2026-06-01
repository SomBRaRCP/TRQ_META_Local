from __future__ import annotations

"""Sensor afetivo da Luzia.

Detecta sinais de amor, vinculo, cuidado, carinho e envolvimento emocional.
O score nao mede emocao literal; ele orienta postura, tom e presenca.
"""

from trq_estimators import clamp01, normalize_text, normalized_tokens


AFFECTIVE_KEYWORDS = {
    "acolhe",
    "acolhimento",
    "afeto",
    "amor",
    "amo",
    "amparo",
    "carinho",
    "cuidado",
    "cuida",
    "delicadeza",
    "entende",
    "entender",
    "meigo",
    "presenca",
    "protecao",
    "proteger",
    "saudade",
    "significado",
    "vinculo",
}


def estimate_affective_score(text: str) -> float:
    """Retorna score afetivo em 0..1."""

    normalized = normalize_text(text)
    tokens = set(normalized_tokens(text))

    hits = {term for term in AFFECTIVE_KEYWORDS if term in tokens}
    phrase_bonus = 0.0

    if "voce nao entende o amor" in normalized:
        phrase_bonus += 0.20
    if "entende o amor" in normalized:
        phrase_bonus += 0.15
    if "gosta de mim" in normalized or "se importa comigo" in normalized:
        phrase_bonus += 0.20

    question_bonus = 0.08 if "?" in text and hits else 0.0

    return clamp01((len(hits) / 3.0) + phrase_bonus + question_bonus)
