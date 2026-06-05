from __future__ import annotations

STIM_TYPES = {
    "teorico":   {"label": "Teórico",   "icon": "⬡", "nqc": "I", "analog": "Monet2"},
    "empirico":  {"label": "Empírico",  "icon": "◎", "nqc": "S", "analog": "Sports1M"},
    "criativo":  {"label": "Criativo",  "icon": "◈", "nqc": "F", "analog": "Cinematic"},
    "reflexivo": {"label": "Reflexivo", "icon": "◉", "nqc": "C", "analog": "Oracle"},
    "sistemico": {"label": "Sistêmico", "icon": "⬢", "nqc": "τ", "analog": "Rendered"},
}

NQC_WEIGHTS = {
    "teorico":   {"I": 0.88, "S": 0.42, "F": 0.30, "C": 0.55, "τ": 0.22},
    "empirico":  {"I": 0.45, "S": 0.90, "F": 0.28, "C": 0.62, "τ": 0.38},
    "criativo":  {"I": 0.32, "S": 0.22, "F": 0.94, "C": 0.44, "τ": 0.58},
    "reflexivo": {"I": 0.52, "S": 0.36, "F": 0.42, "C": 0.91, "τ": 0.41},
    "sistemico": {"I": 0.62, "S": 0.58, "F": 0.46, "C": 0.52, "τ": 0.97},
    "default":   {"I": 0.25, "S": 0.25, "F": 0.25, "C": 0.25, "τ": 0.25},
}

COEF = {
    "alpha": 0.42,
    "beta": 0.06,
    "delta": 0.30,
    "gamma": 0.28,
    "lambda": 0.18,
    "threshold": 62.0,
}

TRQ_TERMS = [
    "nqc", "nqcs", "trq", "coerência", "coerencia", "informação", "informacao",
    "informacional", "quântico", "quantico", "quântica", "quantica", "convergência",
    "convergencia", "torção", "torcao", "emergência", "emergencia", "emergente",
    "regional", "regionalidade", "luzia", "substrato", "campo", "geometria", "escala",
    "formalismo", "lindblad", "grafo", "memória", "memoria", "proofreading", "co-registro",
    "microns", "sinapse", "sinapses", "conectoma", "connectomics",
]

VAGUE_TERMS = [
    "talvez", "poderia", "de certa forma", "de alguma maneira", "meio que", "quem sabe",
    "possivelmente", "eventualmente", "provavelmente", "aparentemente", "de algum modo",
]

TRQ_REFERENCE = """
Teoria da Regionalidade Quântica, Núcleos Quânticos de Convergência, coerência
informacional, grafo de memória, co-registro funcional-estrutural, proofreading,
expansão regional, métricas I S F D A, MICrONS, conectoma, sinapses, resposta
funcional, estrutura, embeddings, memória verificável, evidência e rastreabilidade.
""".strip()
