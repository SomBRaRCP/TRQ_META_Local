import { useState } from "react";
import { runLuziaPipeline } from "./apiClient";

export default function LuziaPipelineRealExample() {
  const [stimulus, setStimulus] = useState("");
  const [stimType, setStimType] = useState("sistemico");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function executar() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await runLuziaPipeline({ stimulus, stimType });
      setResult(data);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 24, background: "#03050d", color: "#b8cce8", minHeight: "100vh" }}>
      <h2>Luzia TRQ META · Backend Real</h2>

      <select value={stimType} onChange={(e) => setStimType(e.target.value)}>
        <option value="teorico">Teórico</option>
        <option value="empirico">Empírico</option>
        <option value="criativo">Criativo</option>
        <option value="reflexivo">Reflexivo</option>
        <option value="sistemico">Sistêmico</option>
      </select>

      <textarea
        value={stimulus}
        onChange={(e) => setStimulus(e.target.value)}
        placeholder="Digite o estímulo semântico..."
        style={{ display: "block", width: "100%", minHeight: 120, marginTop: 12 }}
      />

      <button onClick={executar} disabled={loading || stimulus.trim().length < 3} style={{ marginTop: 12 }}>
        {loading ? "Processando..." : "Executar pipeline real"}
      </button>

      {error && <pre style={{ color: "#e84545" }}>{error}</pre>}

      {result && (
        <div style={{ marginTop: 24 }}>
          <h3>Resposta</h3>
          <p>{result.response}</p>

          <h3>Métricas</h3>
          <pre>{JSON.stringify(result.metrics, null, 2)}</pre>

          <h3>Decisão</h3>
          <pre>{JSON.stringify(result.decision, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
