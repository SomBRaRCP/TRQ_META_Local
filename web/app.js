const messages = document.querySelector("#messages");
const promptForm = document.querySelector("#promptForm");
const promptInput = document.querySelector("#promptInput");
const sendButton = document.querySelector("#sendButton");
const metricsGrid = document.querySelector("#metricsGrid");
const bodyGrid = document.querySelector("#bodyGrid");
const memoryList = document.querySelector("#memoryList");
const memoryQuery = document.querySelector("#memoryQuery");
const modeToggle = document.querySelector("#modeToggle");
const stimType = document.querySelector("#stimType");
const pipelineGrid = document.querySelector("#pipelineGrid");
const pipelineRuns = document.querySelector("#pipelineRuns");

// Modo da interface: "chat" (7860, comportamento original) ou "pipeline"
// (aciona o Pipeline Real em 8000 por proxy e mostra as métricas TRQ reais).
let mode = "chat";

const luziaHero = document.querySelector("#luziaHero");
const luziaPersonaImg = document.querySelector("#luziaPersonaImg");
const luziaParticles = document.querySelector("#luziaParticles");
const luziaMood = document.querySelector("#luziaMood");
const luziaRegime = document.querySelector("#luziaRegime");
const luziaTier = document.querySelector("#luziaTier");
const luziaScore = document.querySelector("#luziaScore");
const luziaDescription = document.querySelector("#luziaDescription");
const readoutRegime = document.querySelector("#readoutRegime");
const readoutTier = document.querySelector("#readoutTier");
const readoutS = document.querySelector("#readoutS");
const readoutM = document.querySelector("#readoutM");
const readoutCLlm = document.querySelector("#readoutCLlm");
const readoutTRQ = document.querySelector("#readoutTRQ");
const readoutExist = document.querySelector("#readoutExist");
const readoutNoise = document.querySelector("#readoutNoise");
const readoutFlow = document.querySelector("#readoutFlow");

const STATE_CLASSES = [
  "state-serena",
  "state-transicao",
  "state-profundo",
  "state-respondendo",
  "state-ouvindo",
];

const bodyState = {
  posture: "serena",
  luminosity: 0.45,
  breath_rate: "normal",
  gaze: "direto",
  voice_tone: "simples",
  presence_level: 0.35,
  inner_phrase: "O estado e simples; responder com precisao basta.",
};

const visualState = {
  I: 0.25,
  S_norm: 0.25,
  F_flow_norm: 0.1,
  M: 0,
  groups: 0,
  gibberish_score: 0,
  affective_score: 0,
  existential_score: 0,
  C_llm: 0,
  regime: "TRANSICAO",
  tier: "fast",
  body_state: bodyState,
};

const messageTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

function numberValue(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function roleLabel(role) {
  if (role === "user") return "Voce";
  if (role === "assistant") return "Luzia";
  if (role === "command") return "Comando";
  return "Sistema";
}

function addMessage(role, text, className = "") {
  const now = new Date();
  const node = document.createElement("div");
  const meta = document.createElement("div");
  const body = document.createElement("div");
  const time = document.createElement("time");

  node.className = `message ${role} ${className}`.trim();
  meta.className = "message-meta";
  body.className = "message-text";
  time.dateTime = now.toISOString();
  time.textContent = messageTimeFormatter.format(now);

  meta.append(roleLabel(role), time);
  body.textContent = text;
  node.append(meta, body);
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return { node, body };
}

function appendMessageText(message, text) {
  if (!message || !text) return;
  message.body.textContent += text;
  messages.scrollTop = messages.scrollHeight;
}

function setGrid(target, data, keys) {
  target.replaceChildren();
  keys.forEach((key) => {
    if (!(key in data)) return;
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = key;
    dd.textContent = String(data[key]);
    target.append(dt, dd);
  });
}

function updateMemoryList(memories) {
  memoryList.replaceChildren();
  if (!memories || memories.length === 0) {
    const empty = document.createElement("div");
    empty.className = "memory-item";
    empty.textContent = "Nenhuma memoria para mostrar.";
    memoryList.appendChild(empty);
    return;
  }

  memories.forEach((memory) => {
    const item = document.createElement("div");
    item.className = "memory-item";
    item.innerHTML = `<strong>[${memory.type}] ${memory.id.slice(0, 8)}</strong>${memory.content}`;
    memoryList.appendChild(item);
  });
}

function buildAvatarStateClass(state = {}) {
  const regime = String(state.regime || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  const posture = String(state.body_state?.posture || state.posture || "").toLowerCase();

  if (state.respondendo || state.is_generating) return "state-respondendo";
  if (state.ouvindo || state.listening) return "state-ouvindo";
  if (regime.includes("profundo") || regime.includes("meta") || posture.includes("introspectiva")) {
    return "state-profundo";
  }
  if (regime.includes("transicao") || regime.includes("transi")) {
    return "state-transicao";
  }
  return "state-serena";
}

export function updateLuziaAvatar(state = {}) {
  if (!luziaHero) return;

  const stateClass = buildAvatarStateClass(state);
  luziaHero.classList.remove(...STATE_CLASSES);
  luziaHero.classList.add(stateClass);

  const glowBase = numberValue(
    state.C_llm ?? state.I ?? state.body_state?.luminosity ?? bodyState.luminosity,
    0.65
  );
  const glow = Math.max(0.45, Math.min(1.35, glowBase));
  const regimeValue = state.regime || visualState.regime || "TRANSICAO";
  const tierValue = state.tier || visualState.tier || "fast";
  const scoreValue = numberValue(state.C_llm ?? state.delta_trq, visualState.C_llm);
  const sValue = numberValue(state.S_norm ?? state.S, visualState.S_norm);
  const mValue = numberValue(state.M, visualState.M);
  const existValue = numberValue(state.existential_score ?? state.exist, visualState.existential_score);
  const noiseValue = numberValue(state.ruido ?? state.noise ?? state.gibberish_score, visualState.gibberish_score);
  const flowValue = numberValue(state.F_flow_norm, visualState.F_flow_norm);
  const moodValue = state.body_state?.posture || state.mood || bodyState.posture || "serena";
  const descriptionValue = state.body_state?.inner_phrase || bodyState.inner_phrase || "O estado e simples; responder com precisao basta.";
  const isResponding = stateClass === "state-respondendo";
  const isDeep = stateClass === "state-profundo";
  const motion = Math.max(0.68, Math.min(1.75, 0.82 + flowValue * 0.86 + scoreValue * 0.22 + (isResponding ? 0.34 : 0) - (isDeep ? 0.18 : 0)));
  const bodySpeed = Math.max(3.2, Math.min(9.4, 6.9 / motion));
  const ribbonSpeed = Math.max(3.8, Math.min(10.8, 8.1 / motion));
  const pulseSpeed = Math.max(1.6, Math.min(4.4, 3.3 / motion));

  luziaHero.style.setProperty("--luzia-glow", glow.toFixed(2));
  luziaHero.style.setProperty("--luzia-flow", flowValue.toFixed(2));
  luziaHero.style.setProperty("--luzia-noise", sValue.toFixed(2));
  luziaHero.style.setProperty("--luzia-motion", motion.toFixed(2));
  luziaHero.style.setProperty("--luzia-body-speed", `${bodySpeed.toFixed(2)}s`);
  luziaHero.style.setProperty("--luzia-ribbon-speed", `${ribbonSpeed.toFixed(2)}s`);
  luziaHero.style.setProperty("--luzia-pulse-speed", `${pulseSpeed.toFixed(2)}s`);

  if (luziaMood) luziaMood.textContent = moodValue;
  if (luziaRegime) luziaRegime.textContent = regimeValue;
  if (luziaTier) luziaTier.textContent = tierValue;
  if (luziaScore) luziaScore.textContent = scoreValue.toFixed(3);
  if (luziaDescription) luziaDescription.textContent = descriptionValue;
  if (readoutRegime) readoutRegime.textContent = regimeValue;
  if (readoutTier) readoutTier.textContent = tierValue;
  if (readoutS) readoutS.textContent = sValue.toFixed(3);
  if (readoutM) readoutM.textContent = mValue.toFixed(3);
  if (readoutCLlm) readoutCLlm.textContent = scoreValue.toFixed(3);
  if (readoutTRQ) readoutTRQ.textContent = scoreValue.toFixed(3);
  if (readoutExist) readoutExist.textContent = String(existValue);
  if (readoutNoise) readoutNoise.textContent = noiseValue.toFixed(3);
  if (readoutFlow) readoutFlow.textContent = flowValue.toFixed(3);
}

export function updateLuziaBodyState(state = {}) {
  if (state.body_state) Object.assign(bodyState, state.body_state);

  Object.assign(visualState, {
    I: numberValue(state.I, visualState.I),
    S_norm: numberValue(state.S_norm, visualState.S_norm),
    F_flow_norm: numberValue(state.F_flow_norm, visualState.F_flow_norm),
    M: numberValue(state.M, visualState.M),
    groups: numberValue(state.groups, visualState.groups),
    gibberish_score: numberValue(state.gibberish_score, visualState.gibberish_score),
    affective_score: numberValue(state.affective_score, visualState.affective_score),
    existential_score: numberValue(state.existential_score, visualState.existential_score),
    C_llm: numberValue(state.C_llm, visualState.C_llm),
    regime: state.regime || visualState.regime,
    tier: state.tier || visualState.tier,
    body_state: bodyState,
  });

  updateLuziaAvatar({ ...visualState, body_state: bodyState });
}

window.updateLuziaAvatar = updateLuziaAvatar;
window.updateLuziaBodyState = updateLuziaBodyState;

function createParticles() {
  if (!luziaParticles) return;
  luziaParticles.replaceChildren();

  for (let i = 0; i < 72; i++) {
    const particle = document.createElement("span");
    particle.style.setProperty("--x", `${Math.random() * 100}%`);
    particle.style.setProperty("--y", `${Math.random() * 100}%`);
    particle.style.setProperty("--s", `${0.45 + Math.random() * 1.85}px`);
    particle.style.setProperty("--d", `${12 + Math.random() * 22}s`);
    particle.style.setProperty("--delay", `${Math.random() * -24}s`);
    particle.style.setProperty("--drift", `${-24 + Math.random() * 48}px`);
    luziaParticles.appendChild(particle);
  }
}

function applyResult(data) {
  if (data.state) {
    setGrid(metricsGrid, data.state, [
      "regime",
      "tier",
      "I",
      "S_norm",
      "F_flow_norm",
      "M",
      "groups",
      "gibberish_score",
      "existential_score",
      "affective_score",
      "relational_score",
      "cognitive_reflection_score",
      "C_llm",
      "r_uni",
      "r_fused",
      "xi_iemf",
      "fusion_regime",
      "fusion_tier",
      "fusion_confidence",
    ]);
  }

  if (data.body_state) {
    Object.assign(bodyState, data.body_state);
    setGrid(bodyGrid, data.body_state, [
      "posture",
      "luminosity",
      "breath_rate",
      "gaze",
      "voice_tone",
      "presence_level",
      "inner_phrase",
    ]);
  }

  if (data.state || data.body_state) {
    updateLuziaBodyState({ ...(data.state || {}), body_state: data.body_state || bodyState });
  }

  if (data.memories) updateMemoryList(data.memories);
}

function parseStreamBlock(block) {
  const lines = block.split("\n");
  let event = "message";
  const dataLines = [];

  lines.forEach((line) => {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  });

  if (!dataLines.length) return null;
  return {
    event,
    data: JSON.parse(dataLines.join("\n")),
  };
}

async function readEventStream(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    let separatorIndex = buffer.indexOf("\n\n");
    while (separatorIndex !== -1) {
      const block = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);
      const parsed = parseStreamBlock(block);
      if (parsed) onEvent(parsed.event, parsed.data);
      separatorIndex = buffer.indexOf("\n\n");
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    const parsed = parseStreamBlock(buffer);
    if (parsed) onEvent(parsed.event, parsed.data);
  }
}

async function sendPrompt(prompt) {
  addMessage("user", prompt);
  sendButton.disabled = true;
  promptInput.disabled = true;
  updateLuziaAvatar({ ...visualState, body_state: bodyState, respondendo: true });

  // Indicador enquanto o modelo carrega/processa; some no 1º token.
  let pending = addMessage("system", "Luzia está pensando…");
  const clearPending = () => {
    if (pending) {
      pending.node.remove();
      pending = null;
    }
  };

  let assistantMessage = null;
  let finalEventReceived = false;

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}`);
    }

    await readEventStream(response, (event, data) => {
      if (event === "state") {
        applyResult(data);
        updateLuziaAvatar({ ...visualState, body_state: bodyState, respondendo: true });
        return;
      }

      if (event === "token") {
        clearPending();
        if (!assistantMessage) {
          assistantMessage = addMessage("assistant", "", "streaming");
        }
        appendMessageText(assistantMessage, data.text || "");
        return;
      }

      if (event === "done") {
        finalEventReceived = true;
        applyResult(data);
        if (data.command) {
          addMessage("command", data.response || data.message || "");
        } else if (!assistantMessage) {
          assistantMessage = addMessage("assistant", data.response || data.message || "");
        } else {
          assistantMessage.node.classList.remove("streaming", "frozen");
          if (data.response && assistantMessage.body.textContent !== data.response) {
            assistantMessage.body.textContent = data.response;
          }
        }
        return;
      }

      if (event === "frozen") {
        finalEventReceived = true;
        applyResult(data);
        if (!assistantMessage) {
          assistantMessage = addMessage("assistant", data.response || "", "frozen");
        }
        assistantMessage.node.classList.remove("streaming");
        assistantMessage.node.classList.add("frozen");
        return;
      }

      if (event === "error") {
        finalEventReceived = true;
        addMessage("system", data.message || "Erro no streaming da resposta.");
      }
    });

    if (!finalEventReceived && assistantMessage) {
      assistantMessage.node.classList.remove("streaming");
      assistantMessage.node.classList.add("frozen");
    }
  } catch (error) {
    addMessage("system", `Erro na interface web: ${error.message}`);
    updateLuziaAvatar({ ...visualState, body_state: bodyState });
  } finally {
    clearPending();
    sendButton.disabled = false;
    promptInput.disabled = false;
    updateLuziaAvatar({ ...visualState, body_state: bodyState });
    promptInput.focus();
  }
}

if (luziaPersonaImg) {
  luziaPersonaImg.addEventListener("error", () => {
    addMessage("system", "Imagem da Luzia nao encontrada em /static/assets/luzia_persona3.png.");
  });
}

function formatNum(value, digits = 1) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(digits) : "?";
}

function renderPipelineMetricsCard(message, data) {
  const metrics = data.metrics || {};
  const coreg = data.coregistration || {};
  const decision = data.decision || {};
  const gen = data.generation || {};
  const expand = Boolean(metrics.expand);

  const card = document.createElement("div");
  card.className = "pipeline-metrics";
  card.innerHTML = `
    <div class="pm-row pm-head">
      <span>PIPELINE REAL · ${data.source || "?"}</span>
      <span>${formatNum(gen.tps, 1)} tk/s</span>
    </div>
    <div class="pm-grid">
      <span>I</span><span>S</span><span>F</span><span>D</span><span>A</span><span>C</span>
      <b>${formatNum(metrics.I)}</b><b>${formatNum(metrics.S)}</b><b>${formatNum(metrics.F)}</b>
      <b>${formatNum(metrics.D)}</b><b>${formatNum(metrics.A)}</b>
      <b class="${expand ? "pm-ok" : "pm-warn"}">${formatNum(metrics.C, 2)}</b>
    </div>
    <div class="pm-row">
      <span>Drift semântico (ligação estímulo↔resposta)</span>
      <b>${formatNum(coreg.stimulus_similarity_score, 1)}%</b>
    </div>
    <div class="pm-row">
      <span>Expansão NQC·${decision.primary_nqc || "?"}</span>
      <b class="${expand ? "pm-ok" : "pm-warn"}">${expand ? "ATINGIDA ✓" : "não atingida ✗"} (limiar ${metrics.threshold ?? "?"})</b>
    </div>
    <div class="pm-reason">${decision.reason || ""}</div>
  `;
  message.node.appendChild(card);
  messages.scrollTop = messages.scrollHeight;
}

function applyPipelineToInspector(data) {
  if (!pipelineGrid) return;
  const metrics = data.metrics || {};
  const coreg = data.coregistration || {};
  const gen = data.generation || {};
  setGrid(
    pipelineGrid,
    {
      source: data.source || "?",
      tps: formatNum(gen.tps, 1),
      I: formatNum(metrics.I),
      S: formatNum(metrics.S),
      F: formatNum(metrics.F),
      D: formatNum(metrics.D),
      A: formatNum(metrics.A),
      C: formatNum(metrics.C, 2),
      threshold: metrics.threshold ?? "?",
      expand: String(Boolean(metrics.expand)),
      stimulus_similarity: formatNum(coreg.stimulus_similarity_score, 1),
      semantic_score: formatNum(coreg.semantic_score, 1),
    },
    [
      "source", "tps", "I", "S", "F", "D", "A", "C",
      "threshold", "expand", "stimulus_similarity", "semantic_score",
    ],
  );
}

async function loadPipelineRuns() {
  if (!pipelineRuns) return;
  try {
    const response = await fetch("/api/pipeline/runs?limit=8");
    const data = await response.json();
    const runs = data.runs || [];
    pipelineRuns.replaceChildren();
    if (!runs.length) {
      const empty = document.createElement("div");
      empty.className = "memory-item";
      empty.textContent = "Nenhuma rodada de pipeline na memória compartilhada ainda.";
      pipelineRuns.appendChild(empty);
      return;
    }
    runs.forEach((run) => {
      const item = document.createElement("div");
      item.className = "memory-item";
      const cVal = run.metrics && run.metrics.C != null ? Number(run.metrics.C).toFixed(1) : "?";
      item.innerHTML = `<strong>[${run.stim_type}] C=${cVal} · ${run.source}</strong>${(run.stimulus || "").slice(0, 90)}`;
      pipelineRuns.appendChild(item);
    });
  } catch (error) {
    /* silencioso: o Pipeline Real (8000) pode estar fora do ar */
  }
}

async function sendPromptPipeline(prompt) {
  if (prompt.length < 3) {
    addMessage("user", prompt);
    addMessage("system", "O modo Pipeline Real precisa de um estímulo com pelo menos 3 caracteres.");
    return;
  }
  addMessage("user", prompt);
  sendButton.disabled = true;
  promptInput.disabled = true;
  updateLuziaAvatar({ ...visualState, body_state: bodyState, respondendo: true });

  // Indicador enquanto o estímulo é embeddado e o modelo carrega; some no 1º token.
  let pending = addMessage("system", "Luzia está pensando…");
  const clearPending = () => {
    if (pending) {
      pending.node.remove();
      pending = null;
    }
  };

  let assistant = null;
  let finished = false;

  try {
    const response = await fetch("/api/pipeline/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, stim_type: stimType?.value || "sistemico" }),
    });
    if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);

    await readEventStream(response, (event, data) => {
      if (event === "token") {
        // Tokens reais do gpt-oss:20b chegando conforme sao gerados.
        clearPending();
        if (!assistant) assistant = addMessage("assistant", "", "pipeline streaming");
        appendMessageText(assistant, data.text || "");
        return;
      }

      if (event === "done") {
        finished = true;
        clearPending();
        if (!assistant) {
          assistant = addMessage("assistant", data.response || "(sem resposta do pipeline)", "pipeline");
        }
        assistant.node.classList.remove("streaming");
        if (data.response && assistant.body.textContent !== data.response) {
          assistant.body.textContent = data.response;
        }
        renderPipelineMetricsCard(assistant, data);
        applyPipelineToInspector(data);
        loadPipelineRuns();
        return;
      }

      if (event === "frozen") {
        finished = true;
        clearPending();
        if (assistant) {
          assistant.node.classList.remove("streaming");
          assistant.node.classList.add("frozen");
        }
        addMessage("system", data.message || "Pipeline interrompido pelo tempo limite.");
        return;
      }

      if (event === "error") {
        finished = true;
        clearPending();
        if (assistant) assistant.node.classList.remove("streaming");
        addMessage("system", data.message || data.error || "Erro no streaming do pipeline.");
      }
    });

    clearPending();
    if (!finished && assistant) assistant.node.classList.remove("streaming");
  } catch (error) {
    clearPending();
    addMessage("system", `Erro na interface (pipeline): ${error.message}`);
  } finally {
    sendButton.disabled = false;
    promptInput.disabled = false;
    updateLuziaAvatar({ ...visualState, body_state: bodyState });
    promptInput.focus();
  }
}

function setMode(next) {
  mode = next;
  const isPipeline = mode === "pipeline";
  modeToggle.dataset.mode = mode;
  modeToggle.textContent = isPipeline ? "Modo: Pipeline Real" : "Modo: Chat";
  modeToggle.classList.toggle("pipeline", isPipeline);
  if (stimType) stimType.hidden = !isPipeline;
  promptInput.placeholder = isPipeline
    ? "Estímulo para o Pipeline Real (8000)…"
    : "Digite para Luzia ou use /ajuda";
  addMessage(
    "system",
    isPipeline
      ? "Modo Pipeline Real ativado — a Luzia roda o estímulo pelo pipeline (8000) e mostra as métricas TRQ reais. (/comandos continuam indo pelo chat.)"
      : "Modo Chat — conversa normal com a Luzia (7860).",
  );
  if (isPipeline) loadPipelineRuns();
}

modeToggle.addEventListener("click", () => setMode(mode === "chat" ? "pipeline" : "chat"));

promptForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt) return;
  promptInput.value = "";
  // Em modo pipeline, comandos com / continuam indo pelo chat (memórias etc.).
  if (mode === "pipeline" && !prompt.startsWith("/")) {
    sendPromptPipeline(prompt);
  } else {
    sendPrompt(prompt);
  }
});

document.querySelector("#helpButton").addEventListener("click", () => sendPrompt("/ajuda"));

document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", () => sendPrompt(button.dataset.command));
});

document.querySelector("#memorySearchButton").addEventListener("click", () => {
  const query = memoryQuery.value.trim();
  if (query) sendPrompt(`/buscar memoria ${query}`);
});

promptInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) promptForm.requestSubmit();
});

createParticles();
updateLuziaBodyState(visualState);
addMessage("system", "Luzia Web pronta. Use /ajuda para comandos ou converse normalmente.");

fetch("/api/memories")
  .then((response) => response.json())
  .then((data) => updateMemoryList(data.memories || []))
  .catch(() => updateMemoryList([]));
