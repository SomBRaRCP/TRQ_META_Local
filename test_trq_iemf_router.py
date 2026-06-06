from __future__ import annotations

from trq_iemf_router import SourceSignal, compute_trq_iemf


def test_prompt_forte_unimodal() -> None:
    sources = [
        SourceSignal(
            name="prompt",
            reliability=0.96,
            confidence=0.95,
            entropy=0.04,
            cost=0.02,
            recency=1.0,
            consistency=0.96,
        )
    ]

    decision = compute_trq_iemf(sources)
    print("\nTESTE 1 - PROMPT FORTE")
    print(decision)

    assert decision.regime in {"UNIMODAL_DOMINANT", "TRANSITION"}
    assert decision.tier in {"fast", "balanced"}
    assert decision.use_tools is False


def test_fusao_dominante() -> None:
    sources = [
        SourceSignal(
            name="prompt",
            reliability=0.32,
            confidence=0.30,
            entropy=0.72,
            cost=0.04,
            recency=1.0,
            consistency=0.38,
        ),
        SourceSignal(
            name="memory",
            reliability=0.62,
            confidence=0.58,
            entropy=0.35,
            cost=0.16,
            recency=0.82,
            consistency=0.72,
        ),
        SourceSignal(
            name="rag",
            reliability=0.68,
            confidence=0.64,
            entropy=0.30,
            cost=0.30,
            recency=0.90,
            consistency=0.76,
        ),
        SourceSignal(
            name="recent_context",
            reliability=0.56,
            confidence=0.52,
            entropy=0.40,
            cost=0.08,
            recency=0.95,
            consistency=0.66,
        ),
    ]

    decision = compute_trq_iemf(sources)
    print("\nTESTE 2 - FUSAO DOMINANTE")
    print(decision)

    assert decision.regime in {"FUSION_DOMINANT", "TRANSITION"}
    assert decision.use_memory is True
    assert decision.use_rag is True


def test_transicao() -> None:
    sources = [
        SourceSignal(
            name="prompt",
            reliability=0.60,
            confidence=0.58,
            entropy=0.34,
            cost=0.03,
            recency=1.0,
            consistency=0.60,
        ),
        SourceSignal(
            name="memory",
            reliability=0.50,
            confidence=0.48,
            entropy=0.44,
            cost=0.18,
            recency=0.72,
            consistency=0.56,
        ),
    ]

    decision = compute_trq_iemf(sources)
    print("\nTESTE 3 - TRANSICAO")
    print(decision)

    assert decision.regime in {
        "TRANSITION",
        "UNIMODAL_DOMINANT",
        "FUSION_DOMINANT",
    }


def test_low_signal() -> None:
    sources = [
        SourceSignal(
            name="prompt",
            reliability=0.10,
            confidence=0.10,
            entropy=0.90,
            cost=0.05,
            recency=1.0,
            consistency=0.10,
        ),
        SourceSignal(
            name="memory",
            reliability=0.05,
            confidence=0.05,
            entropy=0.90,
            cost=0.20,
            recency=0.20,
            consistency=0.05,
        ),
    ]

    decision = compute_trq_iemf(sources)
    print("\nTESTE 4 - LOW SIGNAL")
    print(decision)

    assert decision.regime == "LOW_SIGNAL"
    assert decision.tier == "clarify"


if __name__ == "__main__":
    test_prompt_forte_unimodal()
    test_fusao_dominante()
    test_transicao()
    test_low_signal()
    print("\nTodos os testes do TRQ-IEMF Router rodaram.")
