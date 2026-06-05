from app.metrics import compute_metrics, compute_oracle_and_nqc_base


def test_metrics_expandable_text():
    text = (
        "A TRQ organiza NQCs como grafo de coerência informacional. "
        "O co-registro entre resposta funcional e estrutura de memória permite proofreading, "
        "sinapses simbólicas e expansão regional verificável."
    )
    metrics = compute_metrics(text, stimulus="TRQ NQC memória", semantic_score=80, grounding_score=70)
    assert metrics["words"] > 10
    assert metrics["I"] > 0
    assert metrics["F"] > 0
    assert "expand" in metrics


def test_oracle_and_nqc_base():
    oracle, nqc = compute_oracle_and_nqc_base("A coerência dos NQCs no pipeline TRQ", "sistemico")
    assert oracle > 0
    assert nqc["τ"] > nqc["I"]
