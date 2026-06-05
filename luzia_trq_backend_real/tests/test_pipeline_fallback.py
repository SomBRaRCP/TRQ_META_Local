import asyncio
from pathlib import Path

from app.pipeline import run_pipeline
from app.storage import PipelineStore


async def _run(tmp_path: Path):
    store = PipelineStore(db_path=tmp_path / "test.sqlite3", jsonl_path=tmp_path / "runs.jsonl")
    result = await run_pipeline(
        stimulus="Integre MICrONS, TRQ e co-registro de memória em um backend real.",
        stim_type="sistemico",
        save=True,
        store=store,
    )
    assert result["id"]
    assert result["metrics"]["words"] > 0
    assert "decision" in result


def test_pipeline_fallback(tmp_path):
    asyncio.run(_run(tmp_path))
