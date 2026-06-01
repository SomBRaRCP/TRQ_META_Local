from __future__ import annotations

"""Configuracao central do TRQ META Local.

Este arquivo concentra valores que os outros modulos usam para nao espalhar
strings, caminhos e coeficientes pelo codigo. Assim, trocar modelo, endpoint
ou parametros do Ollama fica simples e nao exige mexer na logica do roteador.
"""

import os
from pathlib import Path


# Pasta raiz do projeto. Tudo que e gerado em runtime parte deste caminho.
BASE_DIR = Path(__file__).resolve().parent

# Pastas de saida: relatorios da bateria e logs do cliente Ollama.
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE = LOGS_DIR / "trq_meta.log"

# Valores padrao do Ollama. Cada um pode ser sobrescrito por variavel de
# ambiente sem alterar codigo.
DEFAULT_MODEL = os.getenv("TRQ_OLLAMA_MODEL", "gpt-oss:20b")
OLLAMA_ENDPOINT = os.getenv("TRQ_OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("TRQ_OLLAMA_TIMEOUT_SECONDS", "600"))
DEFAULT_TEMPERATURE = float(os.getenv("TRQ_TEMPERATURE", "0.2"))
DEFAULT_NUM_CTX = int(os.getenv("TRQ_NUM_CTX", "2048"))

# Ajustes opcionais de runtime. O Ollama decide o offload CUDA/CPU; aqui apenas
# encaminhamos opcoes quando o usuario informa explicitamente.
DEFAULT_NUM_GPU = os.getenv("TRQ_NUM_GPU")
DEFAULT_NUM_THREAD = os.getenv("TRQ_NUM_THREAD")

# Coeficientes canonicos usados na formula C_llm.
COEFFICIENTS = {
    "Humano tecnico": {"alpha": 1.20, "beta": 1.00, "delta": 0.80},
    "LLM leve": {"alpha": 1.30, "beta": 1.15, "delta": 0.75},
    "LLM medio": {"alpha": 1.40, "beta": 1.30, "delta": 0.70},
    "LLM denso": {"alpha": 1.55, "beta": 1.50, "delta": 0.65},
    "LLM frontier": {"alpha": 1.70, "beta": 1.75, "delta": 0.60},
    "LLM raciocinio": {"alpha": 1.60, "beta": 1.90, "delta": 0.55},
}

# Mapeia o tier operacional do roteador para o perfil de coeficientes.
# Nesta versao todos chamam o mesmo modelo, mas o calculo de C_llm precisa
# saber qual familia de coeficientes aplicar.
ROUTE_TO_COEFFICIENT_PROFILE = {
    "fast": "LLM denso",
    "fast/default": "LLM denso",
    "default": "LLM denso",
    "deep": "LLM denso",
    "deep+": "LLM raciocinio",
}

# Vocabulos que aumentam levemente o estimador heuristico de informacao I.
# Eles nao provam qualidade semantica; apenas indicam densidade tecnica.
TECHNICAL_TERMS = {
    "api",
    "algoritmo",
    "analise",
    "arquitetura",
    "atomica",
    "calculo",
    "classe",
    "computacional",
    "continuidade",
    "cuda",
    "dados",
    "derivo",
    "derivar",
    "denso",
    "entropia",
    "equacao",
    "escala",
    "fallback",
    "fisica",
    "fluxo",
    "fotossintese",
    "gap",
    "gpu",
    "heuristica",
    "informacional",
    "java",
    "linguagem",
    "matriz",
    "memoria",
    "metrica",
    "modelo",
    "nqc",
    "objeto",
    "ollama",
    "persistente",
    "principio",
    "probabilidade",
    "processo",
    "python",
    "quantico",
    "quantizacao",
    "quantizo",
    "regime",
    "ressona",
    "roteador",
    "sistema",
    "tensor",
    "tecnica",
    "tecnico",
    "trq",
    "validacao",
    "variacional",
}

# Palavras comuns removidas da analise de repeticao/coerencia. Isso evita que
# artigos e preposicoes inflacionem a coesao topical.
STOPWORDS = {
    "a",
    "ao",
    "as",
    "com",
    "da",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "entre",
    "essa",
    "esse",
    "esta",
    "isso",
    "me",
    "na",
    "no",
    "o",
    "os",
    "para",
    "por",
    "que",
    "se",
    "so",
    "um",
    "uma",
}


def ensure_runtime_dirs() -> None:
    """Garante que as pastas de saida existam antes de gravar arquivos."""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
