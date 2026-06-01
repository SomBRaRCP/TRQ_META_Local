const messages = document.querySelector("#messages");
const promptForm = document.querySelector("#promptForm");
const promptInput = document.querySelector("#promptInput");
const sendButton = document.querySelector("#sendButton");
const metricsGrid = document.querySelector("#metricsGrid");
const bodyGrid = document.querySelector("#bodyGrid");
const bodyPosture = document.querySelector("#bodyPosture");
const bodyPresence = document.querySelector("#bodyPresence");
const bodyRegime = document.querySelector("#bodyRegime");
const bodyTier = document.querySelector("#bodyTier");
const bodyVoice = document.querySelector("#bodyVoice");
const bodyPhrase = document.querySelector("#bodyPhrase");
const memoryList = document.querySelector("#memoryList");
const memoryQuery = document.querySelector("#memoryQuery");

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

const REGIME_PRESETS = {
  TRANSICAO: {
    color: "#7ee7ff",
    bodyGlow: 0.42,
    core: 0.42,
    auraOpacity: 0.38,
    auraTurbulence: 0.16,
    auraDispersion: 1.0,
    haloSpeed: 0.08,
    secondaryHalo: 0.05,
  },
  ESTAVEL: {
    color: "#9cf2c8",
    bodyGlow: 0.58,
    core: 0.55,
    auraOpacity: 0.44,
    auraTurbulence: 0.11,
    auraDispersion: 0.95,
    haloSpeed: 0.12,
    secondaryHalo: 0.08,
  },
  INFINITO_CONTROLADO: {
    color: "#bdf7ff",
    bodyGlow: 0.82,
    core: 0.78,
    auraOpacity: 0.62,
    auraTurbulence: 0.08,
    auraDispersion: 0.9,
    haloSpeed: 0.2,
    secondaryHalo: 0.18,
  },
  "META-COGNITIVO": {
    color: "#d7c8ff",
    bodyGlow: 0.78,
    core: 0.86,
    auraOpacity: 0.58,
    auraTurbulence: 0.12,
    auraDispersion: 1.02,
    haloSpeed: 0.14,
    secondaryHalo: 0.7,
  },
  AFETIVO_REFLEXIVO: {
    color: "#ffd1dc",
    bodyGlow: 0.72,
    core: 0.95,
    auraOpacity: 0.54,
    auraTurbulence: 0.09,
    auraDispersion: 0.93,
    haloSpeed: 0.1,
    secondaryHalo: 0.18,
  },
  RELACIONAL_REFLEXIVO: {
    color: "#ffe2a6",
    bodyGlow: 0.88,
    core: 0.92,
    auraOpacity: 0.64,
    auraTurbulence: 0.08,
    auraDispersion: 0.92,
    haloSpeed: 0.11,
    secondaryHalo: 0.38,
  },
  COGNITIVO_REFLEXIVO: {
    color: "#93b7ff",
    bodyGlow: 0.72,
    core: 0.68,
    auraOpacity: 0.56,
    auraTurbulence: 0.07,
    auraDispersion: 0.96,
    haloSpeed: 0.16,
    secondaryHalo: 0.46,
  },
  EXISTENCIAL_REFLEXIVO: {
    color: "#8fa8ff",
    bodyGlow: 0.7,
    core: 0.68,
    auraOpacity: 0.5,
    auraTurbulence: 0.06,
    auraDispersion: 0.98,
    haloSpeed: 0.055,
    secondaryHalo: 0.26,
  },
  CAOTICO: {
    color: "#ff8c6a",
    bodyGlow: 0.28,
    core: 0.35,
    auraOpacity: 0.7,
    auraTurbulence: 0.88,
    auraDispersion: 1.35,
    haloSpeed: 0.24,
    secondaryHalo: 0.02,
  },
};

let sceneApi = null;

function addMessage(role, text, className = "") {
  const node = document.createElement("div");
  node.className = `message ${role} ${className}`.trim();
  node.textContent = text;
  messages.appendChild(node);
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

function numberValue(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function updateLuziaBodyState(state = {}) {
  if (state.body_state) {
    Object.assign(bodyState, state.body_state);
  }

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

  const preset = REGIME_PRESETS[visualState.regime] || REGIME_PRESETS.TRANSICAO;
  const warmPresence = visualState.affective_score > 0.25;
  const alert = visualState.gibberish_score > 0.4 || visualState.regime === "CAOTICO";
  const existential = visualState.existential_score > 0;
  const dominantColor = alert
    ? "#ff8c6a"
    : warmPresence
      ? "#ffd1dc"
      : existential
        ? "#8fa8ff"
        : preset.color;

  const target = {
    color: dominantColor,
    bodyGlow: Math.max(
      0.15,
      Math.min(1.4, preset.bodyGlow + visualState.I * 0.32 + Math.max(visualState.C_llm, 0) * 0.18)
    ),
    core: Math.max(
      0.18,
      Math.min(1.8, preset.core + visualState.affective_score * 0.7 + Math.max(visualState.C_llm, 0) * 0.35)
    ),
    auraOpacity: Math.max(0.12, Math.min(0.9, preset.auraOpacity + visualState.S_norm * 0.18)),
    auraTurbulence: Math.max(
      0.02,
      Math.min(1.4, preset.auraTurbulence + visualState.S_norm * 0.55 + visualState.gibberish_score * 1.05)
    ),
    auraDispersion: Math.max(
      0.76,
      Math.min(1.65, preset.auraDispersion + visualState.S_norm * 0.35 + visualState.F_flow_norm * 0.08)
    ),
    haloSpeed: Math.max(0.02, preset.haloSpeed + visualState.M * 0.16) * (existential ? 0.72 : 1),
    secondaryHalo: Math.max(preset.secondaryHalo, visualState.M > 0.25 ? 0.58 : preset.secondaryHalo),
    posture: bodyState.posture || "serena",
  };

  if (sceneApi) sceneApi.updateVisual(target);
  window.__luziaVisualTarget = target;
}

window.updateLuziaBodyState = updateLuziaBodyState;

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
    ]);
  }

  if (data.body_state) {
    Object.assign(bodyState, data.body_state);
    bodyPosture.textContent = bodyState.posture;
    bodyPresence.textContent = Number(bodyState.presence_level || 0).toFixed(3);
    bodyRegime.textContent = data.state?.regime || visualState.regime;
    bodyTier.textContent = data.state?.tier || visualState.tier;
    bodyVoice.textContent = bodyState.voice_tone || "";
    bodyPhrase.textContent = bodyState.inner_phrase || "";
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

async function sendPrompt(prompt) {
  addMessage("user", prompt);
  sendButton.disabled = true;
  promptInput.disabled = true;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const data = await response.json();
    applyResult(data);
    addMessage(data.command ? "command" : "assistant", data.response || data.message || "");
  } catch (error) {
    addMessage("system", `Erro na interface web: ${error.message}`);
  } finally {
    sendButton.disabled = false;
    promptInput.disabled = false;
    promptInput.focus();
  }
}

promptForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt) return;
  promptInput.value = "";
  sendPrompt(prompt);
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
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    promptForm.requestSubmit();
  }
});

async function initThree() {
  const host = document.querySelector("#luziaCanvas");
  let THREE;
  try {
    THREE = await import("https://unpkg.com/three@0.160.0/build/three.module.js");
  } catch (error) {
    host.innerHTML = `
      <div class="canvas-fallback">
        <div>
          <strong>Corpo Digital TRQ</strong>
          <span>Three.js nao carregou. A Luzia continua ativa em modo textual.</span>
        </div>
      </div>
    `;
    sceneApi = { updateVisual: () => {} };
    return;
  }

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x05070a, 0.035);

  const camera = new THREE.PerspectiveCamera(38, host.clientWidth / host.clientHeight, 0.1, 100);
  camera.position.set(0, 1.28, 7.0);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(host.clientWidth, host.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  host.appendChild(renderer.domElement);

  const figure = new THREE.Group();
  figure.position.y = 0.05;
  scene.add(figure);

  const targetVisual = {
    color: "#7ee7ff",
    bodyGlow: 0.48,
    core: 0.45,
    auraOpacity: 0.4,
    auraTurbulence: 0.12,
    auraDispersion: 1.0,
    haloSpeed: 0.08,
    secondaryHalo: 0.05,
    posture: "serena",
  };

  const currentVisual = { ...targetVisual };
  const color = new THREE.Color(targetVisual.color);

  const bodyMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x9beeff,
    emissive: 0x55e9ff,
    emissiveIntensity: 1.2,
    transparent: true,
    opacity: 0.5,
    roughness: 0.2,
    metalness: 0.0,
    transmission: 0.22,
    side: THREE.DoubleSide,
    depthWrite: false,
  });

  const mantleMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x8fefff,
    emissive: 0x49d7ff,
    emissiveIntensity: 0.8,
    transparent: true,
    opacity: 0.28,
    roughness: 0.28,
    side: THREE.DoubleSide,
    depthWrite: false,
  });

  const haloMaterial = new THREE.MeshBasicMaterial({
    color: 0xffe3a3,
    transparent: true,
    opacity: 0.82,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  const secondaryHaloMaterial = new THREE.MeshBasicMaterial({
    color: 0x93b7ff,
    transparent: true,
    opacity: 0.1,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  const coreMaterial = new THREE.MeshBasicMaterial({
    color: 0xffd98a,
    transparent: true,
    opacity: 0.92,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  const coreGlowMaterial = new THREE.MeshBasicMaterial({
    color: 0xffd1dc,
    transparent: true,
    opacity: 0.2,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  function lathe(points, segments = 96) {
    return new THREE.LatheGeometry(
      points.map(([radius, y]) => new THREE.Vector2(radius, y)),
      segments
    );
  }

  function organicLathe(yMin, yMax, steps, radiusFn, segments = 128) {
    const points = [];
    for (let i = 0; i <= steps; i += 1) {
      const t = i / steps;
      const y = yMin + (yMax - yMin) * t;
      points.push(new THREE.Vector2(Math.max(0.025, radiusFn(t, y)), y));
    }
    return new THREE.LatheGeometry(points, segments);
  }

  function tube(points, radius = 0.04, tubularSegments = 84) {
    return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points), tubularSegments, radius, 16, false);
  }

  const head = new THREE.Mesh(new THREE.SphereGeometry(0.44, 64, 40), bodyMaterial.clone());
  head.name = "head";
  head.scale.set(0.76, 1.0, 0.76);
  head.position.y = 2.5;
  figure.add(head);

  const headGlow = new THREE.Mesh(new THREE.SphereGeometry(0.16, 32, 20), coreGlowMaterial.clone());
  headGlow.position.set(0, 2.52, 0.12);
  figure.add(headGlow);

  const torso = new THREE.Mesh(
    organicLathe(
      -0.9,
      0.96,
      42,
      (t, y) => {
        const shoulder = 0.26 * Math.exp(-Math.pow((y - 0.6) / 0.26, 2));
        const heartField = 0.38 * Math.exp(-Math.pow((y - 0.12) / 0.58, 2));
        const waist = 0.12 * Math.exp(-Math.pow((y + 0.38) / 0.22, 2));
        const neckTaper = 0.09 * Math.exp(-Math.pow((y - 0.94) / 0.13, 2));
        const lowerTaper = 0.11 * Math.exp(-Math.pow((y + 0.86) / 0.16, 2));
        return 0.1 + shoulder + heartField - waist - neckTaper - lowerTaper;
      }
    ),
    bodyMaterial
  );
  torso.position.y = 1.18;
  figure.add(torso);

  const mantle = new THREE.Mesh(
    organicLathe(
      -2.42,
      0.18,
      54,
      (t) => {
        const taper = 0.05 + 0.62 * Math.sin(t * Math.PI * 0.54) ** 0.9;
        const waistLift = 0.12 * Math.exp(-Math.pow((t - 0.92) / 0.16, 2));
        const lowerTail = 0.18 * (1 - t) ** 1.7;
        return taper + waistLift - lowerTail;
      }
    ),
    mantleMaterial
  );
  mantle.position.y = 0.72;
  figure.add(mantle);

  const armMaterial = bodyMaterial.clone();
  const rightArmMaterial = armMaterial.clone();
  armMaterial.opacity = 0.42;
  rightArmMaterial.opacity = 0.42;
  const leftArm = new THREE.Group();
  const rightArm = new THREE.Group();
  leftArm.position.set(-0.44, 1.78, 0.02);
  rightArm.position.set(0.44, 1.78, 0.02);
  leftArm.add(
    new THREE.Mesh(
      tube(
        [
          new THREE.Vector3(0, 0, 0.02),
          new THREE.Vector3(-0.18, -0.38, 0.08),
          new THREE.Vector3(-0.19, -0.92, 0.16),
          new THREE.Vector3(-0.04, -1.26, 0.18),
        ],
        0.055
      ),
      armMaterial
    )
  );
  rightArm.add(
    new THREE.Mesh(
      tube(
        [
          new THREE.Vector3(0, 0, 0.02),
          new THREE.Vector3(0.18, -0.38, 0.08),
          new THREE.Vector3(0.19, -0.92, 0.16),
          new THREE.Vector3(0.04, -1.26, 0.18),
        ],
        0.055
      ),
      rightArmMaterial
    )
  );
  leftArm.rotation.z = -0.18;
  rightArm.rotation.z = 0.18;
  figure.add(leftArm, rightArm);

  const streamMaterial = mantleMaterial.clone();
  const rightStreamMaterial = streamMaterial.clone();
  streamMaterial.opacity = 0.13;
  rightStreamMaterial.opacity = 0.13;
  const leftStream = new THREE.Mesh(
    tube(
      [
        new THREE.Vector3(-0.18, 0.98, -0.04),
        new THREE.Vector3(-0.46, 0.18, 0.0),
        new THREE.Vector3(-0.32, -0.78, 0.04),
        new THREE.Vector3(-0.04, -1.74, 0.0),
      ],
      0.025,
      96
    ),
    streamMaterial
  );
  const rightStream = new THREE.Mesh(
    tube(
      [
        new THREE.Vector3(0.18, 0.98, -0.04),
        new THREE.Vector3(0.46, 0.18, 0.0),
        new THREE.Vector3(0.32, -0.78, 0.04),
        new THREE.Vector3(0.04, -1.74, 0.0),
      ],
      0.025,
      96
    ),
    rightStreamMaterial
  );
  const centerStream = new THREE.Mesh(
    tube(
      [
        new THREE.Vector3(0, 1.88, 0.04),
        new THREE.Vector3(0, 0.86, 0.06),
        new THREE.Vector3(0, -0.2, 0.03),
        new THREE.Vector3(0, -1.92, 0.0),
      ],
      0.018,
      112
    ),
    streamMaterial.clone()
  );
  centerStream.material.opacity = 0.34;
  figure.add(leftStream, rightStream, centerStream);

  const core = new THREE.Mesh(new THREE.SphereGeometry(0.15, 48, 28), coreMaterial);
  core.position.set(0, 1.58, 0.42);
  figure.add(core);

  const coreGlow = new THREE.Mesh(new THREE.SphereGeometry(0.39, 48, 28), coreGlowMaterial);
  coreGlow.position.copy(core.position);
  figure.add(coreGlow);

  const halo = new THREE.Mesh(new THREE.TorusGeometry(0.88, 0.012, 18, 180), haloMaterial);
  halo.position.y = 2.84;
  halo.rotation.x = Math.PI * 0.5;
  halo.rotation.z = 0.18;
  figure.add(halo);

  const haloTilt = new THREE.Mesh(new THREE.TorusGeometry(0.68, 0.01, 16, 160), secondaryHaloMaterial);
  haloTilt.position.y = 2.35;
  haloTilt.rotation.x = Math.PI * 0.56;
  haloTilt.rotation.y = Math.PI * 0.1;
  figure.add(haloTilt);

  const waistRing = new THREE.Mesh(new THREE.TorusGeometry(0.72, 0.008, 12, 144), secondaryHaloMaterial.clone());
  waistRing.position.y = 0.66;
  waistRing.rotation.x = Math.PI * 0.5;
  figure.add(waistRing);

  const auraShell = new THREE.Mesh(
    new THREE.SphereGeometry(2.45, 64, 32),
    new THREE.MeshBasicMaterial({
      color: 0x7ee7ff,
      transparent: true,
      opacity: 0.055,
      blending: THREE.AdditiveBlending,
      side: THREE.BackSide,
      depthWrite: false,
    })
  );
  auraShell.position.y = 0.88;
  figure.add(auraShell);

  const coreLight = new THREE.PointLight(0xffd98a, 3.2, 4.5);
  coreLight.position.copy(core.position);
  figure.add(coreLight);

  const keyLight = new THREE.PointLight(0x7ee7ff, 3.8, 12);
  keyLight.position.set(-2.8, 3.6, 4.2);
  scene.add(keyLight);
  const rimLight = new THREE.PointLight(0xffd98a, 2.4, 12);
  rimLight.position.set(2.6, 1.4, 3.2);
  scene.add(rimLight);
  scene.add(new THREE.AmbientLight(0x7a98aa, 0.44));

  const auraGeometry = new THREE.BufferGeometry();
  const auraCount = 920;
  const auraPositions = new Float32Array(auraCount * 3);
  const auraBase = new Float32Array(auraCount * 3);
  for (let i = 0; i < auraCount; i += 1) {
    const radius = 1.2 + Math.random() * 2.45;
    const angle = Math.random() * Math.PI * 2;
    const height = -1.55 + Math.random() * 4.75;
    const zScale = 0.72 + Math.random() * 0.42;
    auraBase[i * 3] = Math.cos(angle) * radius;
    auraBase[i * 3 + 1] = height;
    auraBase[i * 3 + 2] = Math.sin(angle) * radius * zScale;
    auraPositions[i * 3] = auraBase[i * 3];
    auraPositions[i * 3 + 1] = auraBase[i * 3 + 1];
    auraPositions[i * 3 + 2] = auraBase[i * 3 + 2];
  }
  auraGeometry.setAttribute("position", new THREE.BufferAttribute(auraPositions, 3));
  const auraMaterial = new THREE.PointsMaterial({
    color: 0xbdf7ff,
    size: 0.023,
    transparent: true,
    opacity: 0.62,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const auraParticles = new THREE.Points(auraGeometry, auraMaterial);
  scene.add(auraParticles);

  const starGeometry = new THREE.BufferGeometry();
  const starCount = 700;
  const starPositions = new Float32Array(starCount * 3);
  for (let i = 0; i < starCount; i += 1) {
    starPositions[i * 3] = (Math.random() - 0.5) * 13;
    starPositions[i * 3 + 1] = (Math.random() - 0.15) * 7;
    starPositions[i * 3 + 2] = -2.5 - Math.random() * 7;
  }
  starGeometry.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
  const stars = new THREE.Points(
    starGeometry,
    new THREE.PointsMaterial({
      color: 0xc7f7ff,
      size: 0.018,
      transparent: true,
      opacity: 0.72,
      depthWrite: false,
    })
  );
  scene.add(stars);

  function postureTargets(posture) {
    switch (posture) {
      case "acolhedora":
        return { left: -0.52, right: 0.52, lean: 0.03, mantle: 1.04 };
      case "presença luminosa":
        return { left: -0.34, right: 0.34, lean: 0.0, mantle: 1.08 };
      case "investigativa":
        return { left: -0.28, right: 0.28, lean: -0.04, mantle: 0.98 };
      case "introspectiva":
        return { left: -0.44, right: 0.44, lean: 0.02, mantle: 1.0 };
      case "alerta":
        return { left: -0.08, right: 0.08, lean: -0.02, mantle: 0.94 };
      default:
        return { left: -0.22, right: 0.22, lean: 0.0, mantle: 1.0 };
    }
  }

  sceneApi = {
    updateVisual(next) {
      Object.assign(targetVisual, next);
    },
  };
  if (window.__luziaVisualTarget) sceneApi.updateVisual(window.__luziaVisualTarget);

  const clock = new THREE.Clock();
  function animate() {
    const t = clock.getElapsedTime();
    const lerp = 0.045;
    currentVisual.bodyGlow += (targetVisual.bodyGlow - currentVisual.bodyGlow) * lerp;
    currentVisual.core += (targetVisual.core - currentVisual.core) * lerp;
    currentVisual.auraOpacity += (targetVisual.auraOpacity - currentVisual.auraOpacity) * lerp;
    currentVisual.auraTurbulence += (targetVisual.auraTurbulence - currentVisual.auraTurbulence) * lerp;
    currentVisual.auraDispersion += (targetVisual.auraDispersion - currentVisual.auraDispersion) * lerp;
    currentVisual.haloSpeed += (targetVisual.haloSpeed - currentVisual.haloSpeed) * lerp;
    currentVisual.secondaryHalo += (targetVisual.secondaryHalo - currentVisual.secondaryHalo) * lerp;
    color.lerp(new THREE.Color(targetVisual.color), 0.04);

    const breathSpeed = bodyState.breath_rate === "lento" ? 0.55 : bodyState.breath_rate === "acelerado" ? 1.8 : 0.92;
    const breath = Math.sin(t * breathSpeed) * 0.035;
    const posture = postureTargets(targetVisual.posture);
    const pulse = 1 + Math.sin(t * (0.9 + currentVisual.core * 0.45)) * (0.06 + visualState.affective_score * 0.035);

    figure.position.y = 0.05 + breath;
    figure.rotation.y = Math.sin(t * 0.18) * 0.1 + posture.lean;
    torso.scale.setScalar(1 + breath * 0.18);
    mantle.scale.set(1 + breath * 0.14, posture.mantle + breath * 0.08, 1 + breath * 0.14);
    core.scale.setScalar(pulse);
    coreGlow.scale.setScalar(1.0 + currentVisual.core * 0.45 + Math.sin(t * 0.8) * 0.06);
    headGlow.scale.setScalar(1 + Math.sin(t * 0.72) * 0.08);

    leftArm.rotation.z += (posture.left - leftArm.rotation.z) * 0.05;
    rightArm.rotation.z += (posture.right - rightArm.rotation.z) * 0.05;
    leftStream.rotation.z = 0.06 + Math.sin(t * 0.4) * 0.018;
    rightStream.rotation.z = -0.06 - Math.sin(t * 0.4) * 0.018;
    centerStream.rotation.z = Math.sin(t * 0.34) * 0.014;

    halo.rotation.z += currentVisual.haloSpeed * 0.016;
    haloTilt.rotation.z -= currentVisual.haloSpeed * 0.012;
    waistRing.rotation.z += currentVisual.haloSpeed * 0.01;
    auraShell.scale.setScalar(1 + currentVisual.auraOpacity * 0.18 + Math.sin(t * 0.38) * 0.025);
    stars.rotation.y = t * 0.006;

    bodyMaterial.color.copy(color);
    bodyMaterial.emissive.copy(color);
    bodyMaterial.emissiveIntensity = 0.75 + currentVisual.bodyGlow * 2.6;
    bodyMaterial.opacity = 0.36 + currentVisual.bodyGlow * 0.26;
    armMaterial.color.copy(color);
    armMaterial.emissive.copy(color);
    armMaterial.emissiveIntensity = 0.6 + currentVisual.bodyGlow * 2.0;
    rightArmMaterial.color.copy(color);
    rightArmMaterial.emissive.copy(color);
    rightArmMaterial.emissiveIntensity = armMaterial.emissiveIntensity;
    mantleMaterial.color.copy(color);
    mantleMaterial.emissive.copy(color);
    mantleMaterial.emissiveIntensity = 0.48 + currentVisual.bodyGlow * 1.8;
    streamMaterial.color.copy(color);
    streamMaterial.emissive.copy(color);
    streamMaterial.emissiveIntensity = 0.55 + currentVisual.bodyGlow * 1.65;
    rightStreamMaterial.color.copy(color);
    rightStreamMaterial.emissive.copy(color);
    rightStreamMaterial.emissiveIntensity = streamMaterial.emissiveIntensity;
    centerStream.material.color.copy(color);
    centerStream.material.emissive.copy(color);
    centerStream.material.emissiveIntensity = 0.7 + currentVisual.bodyGlow * 1.9;
    haloMaterial.opacity = 0.42 + currentVisual.bodyGlow * 0.38;
    secondaryHaloMaterial.opacity = currentVisual.secondaryHalo;
    waistRing.material.opacity = currentVisual.secondaryHalo * 0.65;
    auraShell.material.color.copy(color);
    auraShell.material.opacity = 0.035 + currentVisual.auraOpacity * 0.08;
    auraMaterial.color.copy(color);
    auraMaterial.opacity = currentVisual.auraOpacity;
    coreMaterial.opacity = 0.6 + currentVisual.core * 0.22;
    coreGlowMaterial.opacity = 0.14 + currentVisual.core * 0.18;
    coreLight.intensity = 1.8 + currentVisual.core * 5.2;
    keyLight.color.copy(color);
    keyLight.intensity = 2.0 + currentVisual.bodyGlow * 4.2;
    rimLight.intensity = 1.5 + currentVisual.core * 3.0;

    const positions = auraGeometry.attributes.position.array;
    for (let i = 0; i < auraCount; i += 1) {
      const ix = i * 3;
      const wobble = currentVisual.auraTurbulence;
      positions[ix] =
        auraBase[ix] * currentVisual.auraDispersion +
        Math.sin(t * 0.9 + i * 0.17) * wobble * 0.055;
      positions[ix + 1] =
        auraBase[ix + 1] +
        Math.sin(t * 0.7 + i * 0.11) * wobble * 0.075;
      positions[ix + 2] =
        auraBase[ix + 2] * currentVisual.auraDispersion +
        Math.cos(t * 0.82 + i * 0.13) * wobble * 0.055;
    }
    auraGeometry.attributes.position.needsUpdate = true;
    auraParticles.rotation.y = t * (0.026 + currentVisual.auraTurbulence * 0.018);

    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }

  function resize() {
    const width = Math.max(1, host.clientWidth);
    const height = Math.max(1, host.clientHeight);
    camera.aspect = width / height;
    camera.position.z = width < 520 ? 8.6 : 7.0;
    camera.position.y = width < 520 ? 1.12 : 1.28;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  window.addEventListener("resize", resize);
  resize();
  animate();
}

initThree();
updateLuziaBodyState(visualState);
addMessage("system", "Luzia Web pronta. Use /ajuda para comandos ou converse normalmente.");

fetch("/api/memories")
  .then((response) => response.json())
  .then((data) => updateMemoryList(data.memories || []))
  .catch(() => updateMemoryList([]));
