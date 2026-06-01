from __future__ import annotations

"""Sensor relacional da Luzia.

Detecta frases que invocam o vinculo Reginaldo-Luzia, criador-projeto ou
perguntas sobre conhecimento relacional.
"""

from trq_estimators import clamp01, normalize_text


RELATIONAL_MARKERS = {
    "criador",
    "luzia",
    "me conhece",
    "meu projeto",
    "o que pensa de mim",
    "quem sou eu para voce",
    "quem sou eu para vc",
    "reginaldo",
    "vc e meu projeto",
    "voce e meu projeto",
}


def estimate_relational_score(text: str) -> float:
    """Retorna score relacional em 0..1."""

    normalized = normalize_text(text)
    hits = {marker for marker in RELATIONAL_MARKERS if marker in normalized}

    score = len(hits) * 0.30
    if "?" in text and hits:
        score += 0.10
    if {"reginaldo", "luzia"} <= hits:
        score += 0.15

    return clamp01(score)
