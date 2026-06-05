from __future__ import annotations

import math
import re
from typing import Any

from app.constants import COEF, NQC_WEIGHTS, TRQ_TERMS, VAGUE_TERMS
from app.vector import tokenize, lexical_overlap_score

_SENTENCE_RE = re.compile(r"[.!?]+")


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def compute_oracle_and_nqc_base(stimulus: str, stim_type: str | None) -> tuple[float, dict[str, float]]:
    words = tokenize(stimulus)
    wc = len(words)
    unique = len(set(words))
    lex = unique / max(wc, 1)
    selected_bonus = 0.12 if stim_type else 0.0
    oracle = clamp((lex * 0.55 + min(wc / 70.0, 1.0) * 0.45 + selected_bonus) * 100)

    weights = NQC_WEIGHTS.get(stim_type or "default", NQC_WEIGHTS["default"])
    base = min(wc / 55.0, 1.0)
    nqc_base = {key: round(value * base * 100, 4) for key, value in weights.items()}
    return oracle, nqc_base


def _sentence_lengths(text: str) -> list[int]:
    sentences = [s.strip() for s in _SENTENCE_RE.split(text or "") if s.strip()]
    return [len(tokenize(s)) for s in sentences]


def _keyword_score(text: str, lex_div: float) -> tuple[float, int, list[str]]:
    low = (text or "").lower()
    hits = [term for term in TRQ_TERMS if term in low]
    score = clamp(len(hits) * 7.0 + lex_div * 30.0)
    return score, len(hits), hits


def compute_metrics(
    text: str,
    *,
    stimulus: str = "",
    semantic_score: float = 0.0,
    grounding_score: float = 0.0,
    stimulus_similarity_score: float | None = None,
) -> dict[str, Any]:
    words = tokenize(text)
    wc = len(words)
    unique = len(set(words))
    lex_div = unique / max(wc, 1)
    sentence_lengths = _sentence_lengths(text)
    sentence_count = len(sentence_lengths)
    mean_len = sum(sentence_lengths) / max(sentence_count, 1)
    variance = sum((length - mean_len) ** 2 for length in sentence_lengths) / max(sentence_count, 1)

    # I — densidade informacional / diversidade léxica.
    I = clamp(lex_div * 88 + (12 if wc > 40 else 6 if wc > 20 else 0))

    # S — entropia estrutural por variação de comprimento sentencial.
    S = clamp(math.sqrt(variance) * 7)

    # F — coerência formal híbrida: palavras-chave + semântica + aterramento.
    keyword_score, hit_count, hits = _keyword_score(text, lex_div)
    semantic_score = clamp(semantic_score)
    grounding_score = clamp(grounding_score)
    F = clamp(0.45 * keyword_score + 0.35 * semantic_score + 0.20 * grounding_score)

    # D — densidade de desenvolvimento.
    len_score = min(wc / 280.0, 1.0)
    concept_density = min(hit_count / 8.0, 1.0)
    sentence_depth = min(mean_len / 18.0, 1.0)
    D = clamp((len_score * 0.5 + concept_density * 0.3 + sentence_depth * 0.2) * 100)

    # A — ambiguidade/vagueza e concisão vazia.
    low = (text or "").lower()
    vague_count = sum(1 for term in VAGUE_TERMS if term in low)
    short_penalty = (40 - wc) * 1.2 if wc < 40 else 0.0
    stimulus_drift_penalty = 0.0

    if stimulus_similarity_score is not None:
        # Similaridade vem em escala 0–100.
        # Drift = quanto a resposta se afastou semanticamente do estímulo.
        drift = 100.0 - clamp(stimulus_similarity_score)

        # Só penaliza afastamento forte. Resposta boa pode expandir o estímulo.
        stimulus_drift_penalty = max(0.0, drift - 35.0) * 0.6

    elif stimulus:
        # Fallback antigo, apenas se não houver embedding.
        overlap = lexical_overlap_score(stimulus, text)
        stimulus_drift_penalty = max(0.0, 0.12 - overlap) * 80.0

    A = clamp(vague_count * 9.0 + short_penalty + stimulus_drift_penalty)

    alpha = COEF["alpha"]
    beta = COEF["beta"]
    delta = COEF["delta"]
    gamma = COEF["gamma"]
    lamb = COEF["lambda"]
    threshold = COEF["threshold"]
    terms = {
        "aI": alpha * I,
        "bS": beta * S,
        "dF": delta * F,
        "gD": gamma * D,
        "lA": lamb * A,
    }
    C_metric = clamp(terms["aI"] - terms["bS"] + terms["dF"] + terms["gD"] - terms["lA"])

    return {
        "I": round(I, 4),
        "S": round(S, 4),
        "F": round(F, 4),
        "D": round(D, 4),
        "A": round(A, 4),
        "C": round(C_metric, 4),
        "terms": {k: round(v, 4) for k, v in terms.items()},
        "threshold": threshold,
        "expand": C_metric > threshold,
        "words": wc,
        "sentences": sentence_count,
        "hybrid_F": {
            "keyword_score": round(keyword_score, 4),
            "semantic_score": round(semantic_score, 4),
            "grounding_score": round(grounding_score, 4),
            "hits": hits,
        },
    }


def update_nqc_state(nqc_base: dict[str, float], metrics: dict[str, Any]) -> dict[str, float]:
    return {
        "I": round(clamp(nqc_base.get("I", 0) + (metrics["I"] - 50) * 0.3), 4),
        "S": round(clamp(nqc_base.get("S", 0) + (metrics["S"] - 50) * 0.2), 4),
        "F": round(clamp(nqc_base.get("F", 0) + (metrics["F"] - 50) * 0.3), 4),
        "C": round(clamp(nqc_base.get("C", 0) + (metrics["C"] - 50) * 0.4), 4),
        "τ": round(clamp(nqc_base.get("τ", 0)), 4),
    }
