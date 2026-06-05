const BACKEND_URL = import.meta?.env?.VITE_LUZIA_BACKEND_URL || "http://127.0.0.1:8000";

export async function runLuziaPipeline({ stimulus, stimType = "sistemico", model, temperature = 0.35 }) {
  const response = await fetch(`${BACKEND_URL}/api/pipeline/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      stimulus,
      stim_type: stimType,
      model: model || undefined,
      temperature,
      save: true,
    }),
  });

  const payload = await response.json();
  if (!response.ok || !payload.ok) {
    throw new Error(payload?.error || payload?.detail || "Falha ao executar pipeline Luzia TRQ META");
  }
  return payload.data;
}

export async function getLuziaHealth() {
  const response = await fetch(`${BACKEND_URL}/health`);
  return response.json();
}
