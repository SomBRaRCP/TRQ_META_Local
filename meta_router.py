from __future__ import annotations

"""Auxiliary metacognitive routing helpers for TRQ-IEMF.

This module converts project-local inputs into SourceSignal objects. It does
not call Ollama and does not change the canonical TRQ formula.
"""

from typing import Any, TypedDict

from trq_estimators import normalize_text
from trq_iemf_router import SourceSignal, TRQIEMFDecision, compute_trq_iemf


class TRQIEMFAux(TypedDict):
    r_uni: float
    r_fused: float
    xi_iemf: float
    fusion_regime: str
    fusion_tier: str
    fusion_confidence: str


def apply_trq_iemf_aux(state: Any, trq_aux: TRQIEMFAux) -> None:
    """Attach TRQ-IEMF observables without replacing core TRQ fields."""

    state["r_uni"] = trq_aux["r_uni"]
    state["r_fused"] = trq_aux["r_fused"]
    state["xi_iemf"] = trq_aux["xi_iemf"]
    state["fusion_regime"] = trq_aux["fusion_regime"]
    state["fusion_tier"] = trq_aux["fusion_tier"]
    state["fusion_confidence"] = trq_aux["fusion_confidence"]
    state["aux"] = {"trq_iemf": dict(trq_aux)}


def _avg_hit_score(hits: list[dict[str, Any]], default: float = 0.50) -> float:
    if not hits:
        return 0.0
    scores = []
    for hit in hits:
        raw = hit.get("score", hit.get("confidence", default))
        try:
            scores.append(float(raw))
        except (TypeError, ValueError):
            scores.append(default)
    return sum(scores) / len(scores)


def estimate_prompt_signal(prompt: str) -> SourceSignal:
    text = (prompt or "").strip()
    if not text:
        return SourceSignal(
            name="prompt",
            reliability=0.0,
            confidence=0.0,
            entropy=1.0,
            cost=0.0,
            recency=0.0,
            consistency=0.0,
            available=False,
        )

    normalized = normalize_text(text)
    length = len(text)
    token_count = len([part for part in normalized.split() if part])

    reliability = min(1.0, max(length / 500.0, token_count / 90.0))
    confidence = 0.82 if length >= 40 else 0.46
    entropy = 0.22 if length >= 40 else 0.62
    consistency = 0.72

    weak_markers = {"???", "nao sei explicar", "confuso", "tanto faz", "sei la"}
    if any(marker in normalized for marker in weak_markers):
        consistency = 0.38
        entropy = 0.70
        confidence = min(confidence, 0.42)

    return SourceSignal(
        name="prompt",
        reliability=reliability,
        confidence=confidence,
        entropy=entropy,
        cost=0.02,
        recency=1.0,
        consistency=consistency,
        available=True,
        metadata={"length": length, "tokens": token_count},
    )


def estimate_memory_signal(memory_hits: list[dict[str, Any]] | None) -> SourceSignal:
    hits = memory_hits or []
    if not hits:
        return SourceSignal(
            name="memory",
            reliability=0.0,
            confidence=0.0,
            entropy=1.0,
            cost=0.0,
            recency=0.0,
            consistency=0.0,
            available=False,
        )

    count = len(hits)
    avg_score = _avg_hit_score(hits)
    return SourceSignal(
        name="memory",
        reliability=min(1.0, avg_score),
        confidence=min(1.0, 0.35 + count * 0.12),
        entropy=max(0.05, 0.60 - count * 0.08),
        cost=0.15,
        recency=0.75,
        consistency=min(1.0, avg_score),
        available=True,
        metadata={"hits": count},
    )


def estimate_rag_signal(rag_hits: list[dict[str, Any]] | None) -> SourceSignal:
    hits = rag_hits or []
    if not hits:
        return SourceSignal(
            name="rag",
            reliability=0.0,
            confidence=0.0,
            entropy=1.0,
            cost=0.0,
            recency=0.0,
            consistency=0.0,
            available=False,
        )

    count = len(hits)
    avg_score = _avg_hit_score(hits)
    return SourceSignal(
        name="rag",
        reliability=min(1.0, avg_score),
        confidence=min(1.0, 0.40 + count * 0.10),
        entropy=max(0.05, 0.55 - count * 0.07),
        cost=0.30,
        recency=0.85,
        consistency=min(1.0, avg_score),
        available=True,
        metadata={"hits": count},
    )


def estimate_recent_context_signal(recent_messages: list[str] | None) -> SourceSignal:
    messages = [message for message in (recent_messages or []) if message]
    if not messages:
        return SourceSignal(
            name="recent_context",
            reliability=0.0,
            confidence=0.0,
            entropy=1.0,
            cost=0.0,
            recency=0.0,
            consistency=0.0,
            available=False,
        )

    count = len(messages)
    total_chars = sum(len(message) for message in messages)
    return SourceSignal(
        name="recent_context",
        reliability=min(1.0, total_chars / 2000.0),
        confidence=min(1.0, 0.30 + count * 0.10),
        entropy=0.35,
        cost=0.10,
        recency=0.95,
        consistency=0.65,
        available=True,
        metadata={"messages": count, "chars": total_chars},
    )


def run_trq_iemf_router(
    prompt: str,
    memory_hits: list[dict[str, Any]] | None = None,
    rag_hits: list[dict[str, Any]] | None = None,
    recent_messages: list[str] | None = None,
) -> tuple[TRQIEMFDecision, TRQIEMFAux]:
    sources = [
        estimate_prompt_signal(prompt),
        estimate_memory_signal(memory_hits),
        estimate_rag_signal(rag_hits),
        estimate_recent_context_signal(recent_messages),
    ]

    decision = compute_trq_iemf(sources)
    trq_aux: TRQIEMFAux = {
        "r_uni": decision.r_uni,
        "r_fused": decision.r_fused,
        "xi_iemf": decision.xi_iemf,
        "fusion_regime": decision.regime,
        "fusion_tier": decision.tier,
        "fusion_confidence": decision.confidence_label,
    }
    return decision, trq_aux
