# Luzia TRQ META — Backend Real

Este pacote transforma o pipeline visual `luzia-trq-pipeline-v2.jsx` em um backend real com:

- FastAPI;
- chamada real ao Ollama local (`/api/generate`);
- embeddings via Ollama (`/api/embeddings` ou `/api/embed`);
- fallback determinístico para desenvolvimento, se autorizado por `LZ_ALLOW_FALLBACK=1`;
- cálculo das métricas `I, S, F, D, A`;
- fórmula `C = αI − βS + δF + γD − λA`;
- co-registro vetorial em SQLite;
- registro completo em JSONL;
- endpoints para executar, consultar histórico e buscar memória semelhante.

## 1. Instalação no Windows PowerShell

```powershell
cd C:\a_pasta\Projetos\TRQ_META_LOCAL
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Ollama

Instale e abra o Ollama. Depois baixe os modelos:

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Se preferir outro modelo, altere no `.env` ou nas variáveis de ambiente:

```powershell
$env:OLLAMA_MODEL="qwen2.5:7b"
$env:OLLAMA_EMBED_MODEL="nomic-embed-text"
```

## 3. Rodar o backend

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Teste:

```powershell
curl http://127.0.0.1:8000/health
```

## 4. Executar pipeline

```powershell
curl -X POST http://127.0.0.1:8000/api/pipeline/run `
  -H "Content-Type: application/json" `
  -d "{\"stimulus\":\"Integre MICrONS, TRQ e memória vetorial.\",\"stim_type\":\"sistemico\"}"
```

## 5. Endpoints

- `GET /health` — status do backend e do Ollama.
- `POST /api/pipeline/run` — executa o pipeline real.
- `GET /api/pipeline/runs?limit=20` — lista execuções recentes.
- `GET /api/pipeline/runs/{id}` — abre uma execução.
- `POST /api/memory/search` — busca memórias semelhantes.

## 6. Ligar ao React

Use `frontend/apiClient.js` no seu app React/Vite e substitua o trecho antigo de `SIM_RESPONSES` pela chamada:

```js
const data = await runLuziaPipeline({ stimulus, stimType: stimType.id });
```

A resposta retorna:

- `response` — texto gerado pelo Ollama;
- `metrics` — I, S, F, D, A e C;
- `decision` — expandir ou manter NQC;
- `coregistration` — memórias semelhantes e scores;
- `nqc` — estado base e estado atualizado.

## 7. Produção sem simulação

Para bloquear fallback e exigir Ollama real:

```powershell
$env:LZ_ALLOW_FALLBACK="0"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Assim, se o Ollama cair, o backend falha explicitamente em vez de fingir resposta.
