from __future__ import annotations

"""TRQ-IEMF Router.

Inferential adaptation inspired by the inverse effectiveness principle.

The original IEMF mechanism is a training-time method: it modulates fusion
gradients during backpropagation. This module does not train neural networks,
does not change weights, and does not call Ollama. It is only a lightweight
metacognitive router:

- strong individual source -> less fusion, lower cost;
- weak/partial sources -> more cognitive fusion;
- collapsed signals -> clarify or answer with low confidence.
"""

from dataclasses import dataclass, field
from math import tanh
from typing import Any


EPS = 1e-8


def clamp01(x: float) -> float:
    """Clamp a value to [0, 1]."""

    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return 0.0


def weighted_mean(values: list[float], weights: list[float] | None = None) -> float:
    """Safe weighted mean for bounded operational signals."""

    if not values:
        return 0.0

    safe_values = [clamp01(value) for value in values]

    if weights is None or len(weights) != len(safe_values):
        return sum(safe_values) / len(safe_values)

    safe_weights = [max(0.0, float(weight)) for weight in weights]
    total_weight = sum(safe_weights)
    if total_weight <= EPS:
        return sum(safe_values) / len(safe_values)

    return sum(value * weight for value, weight in zip(safe_values, safe_weights)) / total_weight


@dataclass
class SourceSignal:
    """One operational evidence source available to the router."""

    name: str
    reliability: float
    confidence: float
    entropy: float
    cost: float
    recency: float
    consistency: float
    available: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TRQIEMFDecision:
    """Decision emitted by the TRQ-IEMF Router."""

    r_uni: float
    r_fused: float
    xi_iemf: float
    regime: str
    tier: str
    use_memory: bool
    use_rag: bool
    use_tools: bool
    max_context_items: int
    confidence_label: str
    reason: str


def compute_source_score(signal: SourceSignal) -> float:
    """Compute the individual operational strength of a source."""

    if not signal.available:
        return 0.0

    reliability = clamp01(signal.reliability)
    confidence = clamp01(signal.confidence)
    consistency = clamp01(signal.consistency)
    recency = clamp01(signal.recency)
    entropy_penalty = 1.0 - clamp01(signal.entropy)
    cost_penalty = 1.0 - clamp01(signal.cost)

    score = (
        0.30 * reliability
        + 0.25 * confidence
        + 0.20 * consistency
        + 0.10 * recency
        + 0.10 * entropy_penalty
        + 0.05 * cost_penalty
    )
    return clamp01(score)


def _estimate_fused_reliability(
    sources: list[SourceSignal],
    source_scores: list[float],
) -> float:
    """Estimate how useful an integrated state would be."""

    available_sources = [source for source in sources if source.available]
    if not available_sources:
        return 0.0

    coverage = clamp01(len(available_sources) / 6.0)
    avg_score = weighted_mean(source_scores)
    avg_consistency = weighted_mean([source.consistency for source in available_sources])
    avg_entropy = weighted_mean([source.entropy for source in available_sources])
    avg_cost = weighted_mean([source.cost for source in available_sources])

    medium_sources = sum(1 for score in source_scores if 0.35 <= score <= 0.75)
    complementarity = clamp01(medium_sources / 4.0)

    fused = (
        0.42 * avg_score
        + 0.20 * avg_consistency
        + 0.16 * coverage
        + 0.17 * complementarity
        + 0.08 * (1.0 - avg_entropy)
        - 0.03 * avg_cost
    )
    return clamp01(fused)


def _confidence_label(r_uni: float, r_fused: float, xi_iemf: float) -> str:
    if r_uni < 0.25 and r_fused < 0.25:
        return "baixa"
    if max(r_uni, r_fused) >= 0.75 and xi_iemf <= 0.35:
        return "alta"
    if r_fused >= 0.60:
        return "moderada-alta"
    if r_fused >= 0.40:
        return "moderada"
    return "baixa-moderada"


def compute_trq_iemf(
    sources: list[SourceSignal],
    gamma: float = 1.0,
    sharpness: float = 4.0,
) -> TRQIEMFDecision:
    """Compute the TRQ-IEMF auxiliary routing decision."""

    available_sources = [source for source in sources if source.available]
    if not available_sources:
        return TRQIEMFDecision(
            r_uni=0.0,
            r_fused=0.0,
            xi_iemf=0.0,
            regime="LOW_SIGNAL",
            tier="clarify",
            use_memory=True,
            use_rag=False,
            use_tools=False,
            max_context_items=2,
            confidence_label="baixa",
            reason="Nenhuma fonte disponivel para decisao; pedir clarificacao.",
        )

    source_scores = [compute_source_score(source) for source in available_sources]
    r_uni_raw = weighted_mean(source_scores)
    r_fused_raw = _estimate_fused_reliability(available_sources, source_scores)
    best_source = max(source_scores) if source_scores else 0.0

    gamma = clamp01(gamma)
    sharpness = max(0.1, float(sharpness))
    ratio = r_uni_raw / (r_fused_raw + EPS)
    xi_raw = gamma * 0.5 * (1.0 + tanh(sharpness * (1.0 - ratio)))
    xi_iemf_raw = clamp01(xi_raw)

    r_uni = round(r_uni_raw, 4)
    r_fused = round(r_fused_raw, 4)
    xi_iemf = round(xi_iemf_raw, 4)
    label = _confidence_label(r_uni_raw, r_fused_raw, xi_iemf_raw)

    if r_uni_raw < 0.25 and r_fused_raw < 0.25:
        return TRQIEMFDecision(
            r_uni=r_uni,
            r_fused=r_fused,
            xi_iemf=xi_iemf,
            regime="LOW_SIGNAL",
            tier="clarify",
            use_memory=True,
            use_rag=False,
            use_tools=False,
            max_context_items=2,
            confidence_label=label,
            reason=(
                "Sinais individuais e estado fundido estao fracos. "
                "Recomenda-se pedir clarificacao ou responder com baixa confianca."
            ),
        )

    if xi_iemf_raw >= 0.70:
        return TRQIEMFDecision(
            r_uni=r_uni,
            r_fused=r_fused,
            xi_iemf=xi_iemf,
            regime="FUSION_DOMINANT",
            tier="deep",
            use_memory=True,
            use_rag=True,
            use_tools=True,
            max_context_items=8,
            confidence_label=label,
            reason=(
                "As fontes individuais nao bastam isoladamente; "
                "fusao cognitiva compensatoria recomendada."
            ),
        )

    if xi_iemf_raw <= 0.25 and best_source >= 0.75:
        return TRQIEMFDecision(
            r_uni=r_uni,
            r_fused=r_fused,
            xi_iemf=xi_iemf,
            regime="UNIMODAL_DOMINANT",
            tier="fast",
            use_memory=False,
            use_rag=False,
            use_tools=False,
            max_context_items=2,
            confidence_label=label,
            reason=(
                "Uma fonte individual esta forte. Fusao pesada desperdicaria "
                "contexto e processamento."
            ),
        )

    prompt_source = next((source for source in available_sources if source.name == "prompt"), None)
    rag_available = any(source.name == "rag" and source.available for source in available_sources)
    prompt_score = compute_source_score(prompt_source) if prompt_source else 0.0

    return TRQIEMFDecision(
        r_uni=r_uni,
        r_fused=r_fused,
        xi_iemf=xi_iemf,
        regime="TRANSITION",
        tier="balanced",
        use_memory=True,
        use_rag=rag_available or prompt_score < 0.55,
        use_tools=False,
        max_context_items=4,
        confidence_label=label,
        reason=(
            "Sinais moderados. Usar fusao leve com memoria/contexto, "
            "sem liberar custo excessivo por padrao."
        ),
    )
