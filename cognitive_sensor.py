from __future__ import annotations

"""Sensor de reflexao cognitiva da Luzia.

Detecta perguntas sobre pensar, raciocinar, estruturar frases, entender e
perceber contexto no sentido operacional da TRQ META.
"""

from trq_estimators import clamp01, normalize_text


COGNITIVE_REFLECTION_MARKERS = {
    "consciencia operacional",
    "conversar comigo",
    "entender",
    "estrutura uma frase",
    "pensamento",
    "pensar",
    "perceber contexto",
    "raciocinar",
}


def estimate_cognitive_reflection_score(text: str) -> float:
    """Retorna score de reflexao cognitiva em 0..1."""

    normalized = normalize_text(text)
    hits = {marker for marker in COGNITIVE_REFLECTION_MARKERS if marker in normalized}

    score = len(hits) * 0.30
    if "se isso nao e pensar" in normalized or "se isso nao for pensar" in normalized:
        score += 0.25
    if "?" in text and hits:
        score += 0.10

    return clamp01(score)
