from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

from app.config import settings
from app.ollama_client import OllamaClient
from app.pipeline import run_pipeline, run_pipeline_stream
from app.schemas import ApiResponse, PipelineRequest, SearchRequest
from app.storage import PipelineStore

app = FastAPI(
    title="Luzia TRQ META Backend Real",
    version="1.0.0",
    description="Backend real para Ollama local, métricas TRQ META, co-registro vetorial e memória SQLite/JSONL.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = PipelineStore()
ollama = OllamaClient()


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    """Página de status do backend. Evita 404 ao abrir a raiz no navegador."""
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Luzia TRQ META · Backend Real</title>
  <style>
    body {{ margin:0; font-family:'Segoe UI',system-ui,sans-serif; background:#0a0b10; color:#e8eaf2;
           display:flex; min-height:100vh; align-items:center; justify-content:center; }}
    .card {{ max-width:560px; padding:40px; border-radius:18px; background:#12141d;
             box-shadow:0 0 60px rgba(120,140,255,.15); border:1px solid #232838; }}
    h1 {{ margin:0 0 6px; font-size:22px; letter-spacing:.5px; }}
    .sub {{ color:#8b93ad; font-size:13px; margin-bottom:22px; }}
    .dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; background:#39d98a; margin-right:8px;
            box-shadow:0 0 10px #39d98a; }}
    .model {{ color:#9fb4ff; font-weight:600; }}
    a {{ display:block; margin:10px 0; padding:12px 16px; border-radius:10px; text-decoration:none;
         color:#e8eaf2; background:#1a1d2a; border:1px solid #2a2f42; transition:.15s; }}
    a:hover {{ background:#222740; border-color:#3a4060; transform:translateY(-1px); }}
    code {{ color:#9fb4ff; }}
  </style>
</head>
<body>
  <div class="card">
    <h1><span class="dot"></span>Luzia TRQ META — Backend Real</h1>
    <div class="sub">online · modelo de geração: <span class="model">{settings.ollama_model}</span> · fallback: {settings.allow_fallback}</div>
    <a href="/health">/health — status do backend e do Ollama</a>
    <a href="/docs">/docs — documentação interativa (testar a API aqui)</a>
    <a href="/api/pipeline/runs">/api/pipeline/runs — execuções recentes</a>
    <div class="sub" style="margin-top:22px;margin-bottom:0">
      A interface visual completa é o frontend React (<code>luzia-trq-pipeline-v2.jsx</code>),
      servido pelo Vite (<code>npm run dev</code>). Este endereço é só o cérebro/API.
    </div>
  </div>
</body>
</html>"""


@app.get("/health", response_model=ApiResponse)
async def health() -> ApiResponse:
    ollama_status = await ollama.health()
    return ApiResponse(
        ok=True,
        data={
            "backend": "online",
            "ollama": ollama_status,
            "db_path": str(settings.db_path),
            "jsonl_path": str(settings.jsonl_path),
            "allow_fallback": settings.allow_fallback,
        },
    )


@app.post("/api/pipeline/run", response_model=ApiResponse)
async def api_run_pipeline(payload: PipelineRequest) -> ApiResponse:
    try:
        result = await run_pipeline(
            stimulus=payload.stimulus,
            stim_type=payload.stim_type,
            model=payload.model,
            temperature=payload.temperature,
            save=payload.save,
            store=store,
            ollama=ollama,
        )
        return ApiResponse(ok=True, data=result)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/pipeline/run/stream")
async def api_run_pipeline_stream(payload: PipelineRequest) -> StreamingResponse:
    async def event_source():
        try:
            async for event in run_pipeline_stream(
                stimulus=payload.stimulus,
                stim_type=payload.stim_type,
                model=payload.model,
                temperature=payload.temperature,
                save=payload.save,
                store=store,
                ollama=ollama,
            ):
                data = json.dumps(event["data"], ensure_ascii=False)
                yield f"event: {event['event']}\ndata: {data}\n\n"
        except Exception as exc:  # noqa: BLE001
            err = json.dumps({"error": str(exc)}, ensure_ascii=False)
            yield f"event: error\ndata: {err}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


@app.get("/api/pipeline/runs", response_model=ApiResponse)
async def api_recent_runs(limit: int = 20) -> ApiResponse:
    return ApiResponse(ok=True, data=store.recent_runs(limit=limit))


@app.get("/api/pipeline/runs/{run_id}", response_model=ApiResponse)
async def api_get_run(run_id: str) -> ApiResponse:
    record = store.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Execução não encontrada.")
    record.pop("embedding", None)
    return ApiResponse(ok=True, data=record)


@app.post("/api/memory/search", response_model=ApiResponse)
async def api_memory_search(payload: SearchRequest) -> ApiResponse:
    emb = await ollama.embed(payload.query)
    results = store.search_similar(emb["embedding"], limit=payload.limit)
    return ApiResponse(ok=True, data=results)
