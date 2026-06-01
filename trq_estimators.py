from __future__ import annotations

"""Estimadores numericos usados pelo roteador TRQ.

Este modulo nao chama Ollama. Ele recebe texto puro e devolve sinais
heuristicos: ruido/gibberish, metacognicao, informacao, entropia, fluxo e
C_llm. Manter isso puro facilita testar a bateria sem depender de servidor.
"""

import math
import re
import unicodedata
from collections import Counter
from typing import Iterable

from config import COEFFICIENTS, ROUTE_TO_COEFFICIENT_PROFILE, STOPWORDS, TECHNICAL_TERMS


# Regex principal de tokenizacao. Ela preserva letras latinas acentuadas,
# letras gregas simples, numeros e alguns simbolos tecnicos comuns.
TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿΑ-ω_+-]+", re.UNICODE)

# Sequencias longas de consoantes costumam indicar token artificial/ruidoso.
CONSONANT_RUN_RE = re.compile(r"[bcdfghjklmnpqrstvwxyz]{4,}")

# Usamos vogais ASCII depois da normalizacao sem acento.
VOWELS = set("aeiou")

# Fragmentos comuns de teclado que aparecem em prompts caoticos.
KEYBOARD_FRAGMENTS = {
    "asdf",
    "jkl",
    "pqow",
    "qwe",
    "qwer",
    "rty",
    "zxc",
}

# Tokens curtos frequentes nao devem pesar como ruido forte. Por exemplo,
# "oi" e "de" sao validos, enquanto "xz" deve levantar suspeita moderada.
SHORT_COMMON = {
    "a",
    "as",
    "de",
    "do",
    "e",
    "eu",
    "me",
    "no",
    "o",
    "oi",
    "os",
    "q",
    "se",
}


def clamp01(value: float) -> float:
    """Limita qualquer numero para a faixa fechada 0..1."""

    return max(0.0, min(1.0, value))


def normalize_text(text: str) -> str:
    """Normaliza texto para comparacoes simples e robustas.

    A funcao coloca em minusculas, remove acentos e descarta caracteres que
    nao cabem em ASCII. Isso evita duplicar detectores para "analise" e
    "analise" com acento, por exemplo.
    """

    normalized = unicodedata.normalize("NFKD", text.lower())
    return normalized.encode("ascii", "ignore").decode("ascii")


def tokenize(text: str) -> list[str]:
    """Quebra o texto em tokens candidatos a palavra/simbolo tecnico."""

    return TOKEN_RE.findall(text.lower())


def normalized_tokens(text: str) -> list[str]:
    """Tokeniza e normaliza cada token antes das metricas."""

    return [normalize_text(token) for token in tokenize(text) if normalize_text(token)]


def relevant_tokens(text: str) -> list[str]:
    """Remove tokens pouco informativos para medir repeticao topical."""

    return [
        token
        for token in normalized_tokens(text)
        if len(token) >= 3 and token not in STOPWORDS and not token.isdigit()
    ]


def count_technical_terms(text: str) -> int:
    """Conta termos tecnicos isolados e algumas expressoes compostas."""

    # Normalizacao permite comparar com o vocabulario ASCII de config.py.
    normalized = normalize_text(text)

    # O set evita contar o mesmo termo isolado duas vezes.
    tokens = set(normalized_tokens(text))
    hits = {term for term in TECHNICAL_TERMS if term in tokens}

    # Algumas ideias tecnicas aparecem como frase, nao como uma palavra unica.
    phrase_hits = {
        "principio variacional",
        "arquitetura informacional",
        "memoria persistente",
        "modelo computacional",
        "equacao de continuidade",
    }

    # Unimos hits de palavra e frase para devolver uma contagem simples.
    hits.update(phrase for phrase in phrase_hits if phrase in normalized)
    return len(hits)


def estimate_gibberish_score(text: str) -> float:
    """Estima quanto do texto parece ruido artificial.

    A regra segue a especificacao: token sem vogal, token com 4+ consoantes e
    fragmentos de teclado aumentam suspeita. Tokens curtos recebem peso menor
    para nao punir frases normais como "Oi.".
    """

    tokens = normalized_tokens(text)
    if not tokens:
        return 0.0

    # Numerador ponderado de tokens suspeitos.
    suspicious_weight = 0.0

    # Denominador ponderado de todos os tokens avaliados.
    total_weight = 0.0

    for token in tokens:
        # Numero puro nao carrega sinal forte de ruido textual.
        if token.isdigit():
            total_weight += 0.2
            continue

        # O peso reduzido para tokens curtos impede distorcao por "q", "de".
        length = len(token)
        if length <= 2:
            weight = 0.25 if token in SHORT_COMMON else 0.50
        elif length == 3:
            weight = 0.85
        else:
            weight = 1.0

        # Detectores locais de suspeita.
        has_vowel = any(char in VOWELS for char in token)
        is_keyboard_fragment = token in KEYBOARD_FRAGMENTS
        is_consonant_run = bool(CONSONANT_RUN_RE.search(token))
        is_short_noise = length <= 2 and not has_vowel and token not in SHORT_COMMON

        # Tokens longos sem vogal, com consoantes demais ou padrao de teclado
        # entram como suspeitos completos.
        if (length >= 3 and not has_vowel) or is_consonant_run or is_keyboard_fragment:
            suspicious_weight += weight

        # Tokens curtissimos sem vogal entram com meia penalidade.
        elif is_short_noise:
            suspicious_weight += weight * 0.5

        total_weight += weight

    # Protecao defensiva para divisao por zero.
    if total_weight == 0:
        return 0.0

    # O resultado final sempre fica entre 0 e 1.
    return clamp01(suspicious_weight / total_weight)


def _has_any(normalized_text: str, phrases: Iterable[str]) -> bool:
    """Atalho para saber se qualquer marcador aparece no texto normalizado."""

    return any(phrase in normalized_text for phrase in phrases)


def compute_M(text: str) -> tuple[float, int]:
    """Calcula M, o sinal metacognitivo, e quantos grupos ativaram.

    O score usa os pesos validados na especificacao v3.0.5. Cada detector
    representa um grupo independente: correcao, plano, incerteza, etc.
    """

    # raw_lower preserva "%" e texto original para a regex de confianca.
    raw_lower = text.lower()

    # normalized facilita detectar frases com ou sem acento.
    normalized = normalize_text(text)

    # Todos os detectores comecam desligados e sao ativados por regras abaixo.
    detectors = {
        "recursive_ref": False,
        "correction": False,
        "hedge": False,
        "plan": False,
        "counterfactual": False,
        "uncertainty": False,
    }

    # G1: auto-correcao, revisao ou indicio de verificacao.
    detectors["correction"] = _has_any(
        normalized,
        {
            "corrigindo",
            "corrige",
            "estava errado",
            "preciso verificar",
            "refazendo",
            "reformulando",
            "revisando",
        },
    )

    # G2: plano/processo sequencial. Exige ao menos dois marcadores ou
    # "primeiro" acompanhado de outro passo.
    sequence_terms = {"primeiro", "segundo", "depois", "entao", "finalmente", "por fim"}
    sequence_hits = {term for term in sequence_terms if term in normalized}
    detectors["plan"] = (
        "primeiro" in sequence_hits
        and bool(sequence_hits - {"primeiro"})
    ) or len(sequence_hits) >= 2

    # G3: hedging probabilistico. A regex evita \b depois de %, como pedido,
    # porque "%" seguido de espaco pode quebrar esse limite de palavra.
    detectors["hedge"] = bool(
        re.search(r"\d{1,3}\s*%.{0,70}(confian|probabil|certez)", raw_lower, flags=re.IGNORECASE)
    )

    # G4: contrafactual, incluindo "considere o oposto" e "e se".
    detectors["counterfactual"] = _has_any(
        normalized,
        {
            "considerando o oposto",
            "considere o oposto",
            "e se",
            "mas e se",
            "na ausencia de",
            "no caso contrario",
        },
    )

    # G5: referencia ao proprio processo, raciocinio ou acao de analise.
    process_terms = {
        "disse antes",
        "estou fazendo",
        "meu modelo",
        "meu procedimento",
        "meu raciocinio",
        "minha analise",
        "o que disse antes",
    }

    # Verbos em primeira pessoa ajudam no caso de prompts como
    # "Primeiro derivo... Depois quantizo...".
    procedural_first_person = {
        "avalio",
        "calculo",
        "derivo",
        "estimo",
        "meco",
        "quantizo",
    }
    detectors["recursive_ref"] = _has_any(normalized, process_terms) or _has_any(
        normalized, procedural_first_person
    )

    # Incerteza/critica ativa o grupo que pede avaliacao de validade.
    detectors["uncertainty"] = _has_any(
        normalized,
        {
            "critica",
            "duvida",
            "esta certo",
            "falsa",
            "hipotese",
            "incerteza",
            "incerto",
            "probabilidade",
            "quais consequencias",
        },
    )

    # Pesos canonicos de M na especificacao.
    weights = {
        "recursive_ref": 0.22,
        "correction": 0.18,
        "hedge": 0.15,
        "plan": 0.10,
        "counterfactual": 0.20,
        "uncertainty": 0.15,
    }

    # Conta grupos ativos para a regra META-COGNITIVO.
    groups_active = sum(1 for active in detectors.values() if active)

    # Soma apenas os pesos dos grupos detectados.
    score = sum(weights[name] for name, active in detectors.items() if active)

    # Bonus pequeno para prompts com multiplos sinais independentes. Ele ajuda
    # a separar meta-cognicao real de uma palavra isolada.
    if groups_active >= 3:
        score += 0.08
    elif groups_active >= 2:
        score += 0.05

    # Retorna score limitado e quantidade bruta de grupos.
    return clamp01(score), groups_active


def estimate_I(text: str) -> float:
    """Estima I, uma informacao/coerencia heuristica.

    Esta versao nao usa embeddings. Ela combina comprimento, termos tecnicos,
    coesao por repeticao moderada, estrutura textual e penalidade por ruido.
    """

    tokens = normalized_tokens(text)
    if not tokens:
        return 0.0

    # Medidas basicas reutilizadas por varios sub-scores.
    token_count = len(tokens)
    relevant = relevant_tokens(text)
    counts = Counter(relevant)

    # Repeticao de termos relevantes sugere topico consistente.
    repeated_terms = sum(count - 1 for count in counts.values() if count > 1)

    # Termos tecnicos aumentam I, mas com teto para nao dominar tudo.
    technical_count = count_technical_terms(text)
    normalized = normalize_text(text)

    # Ruido derruba I no final.
    gibberish_score = estimate_gibberish_score(text)

    # Base minima depende de haver mais que uma saudacao/fragmento curto.
    base = 0.08 if token_count > 2 else 0.02

    # Cresce com comprimento, mas usa log para saturar em textos longos.
    length_score = min(0.26, math.log1p(token_count) / math.log1p(80) * 0.36)

    # Cada termo tecnico soma ate um limite.
    technical_score = min(0.36, technical_count * 0.14)

    # Repeticao moderada de termos relevantes aumenta coesao.
    cohesion_score = min(0.16, (repeated_terms / max(1, len(relevant))) * 0.55)

    # Verbos de comando analitico indicam tarefa com mais conteudo.
    command_terms = {
        "considere",
        "critica",
        "derive",
        "diferenca",
        "explique",
        "explica",
        "monte",
        "modelo",
    }

    # Comeca neutro e sobe conforme a intencao detectada.
    command_score = 0.0
    if _has_any(normalized, command_terms):
        command_score = 0.12
    elif _has_any(normalized, {"corrige", "faz", "lista"}):
        command_score = 0.06

    # Estrutura explicita tambem indica melhor fluxo informacional.
    structure_score = 0.0
    if any(mark in text for mark in ("?", ":", ";", ".")):
        structure_score += 0.03
    if _has_any(normalized, {"primeiro", "depois", "finalmente", "por fim"}):
        structure_score += 0.07
    if "\n" in text or re.search(r"(^|\n)\s*[-*0-9]+[.)-]?\s+", text):
        structure_score += 0.04
    structure_score = min(0.12, structure_score)

    # Prompts curtos tecnicos, como "Java e Python?", nao devem ser tratados
    # como vazios so por terem poucos tokens.
    short_technical_rescue = 0.0
    if technical_count >= 1 and token_count <= 5:
        short_technical_rescue = 0.10
    elif technical_count >= 2:
        short_technical_rescue = 0.05

    # Bonus para dominio tecnico denso.
    dense_domain_bonus = 0.05 if technical_count >= 4 else 0.0

    # Saudacoes ou fragmentos muito curtos ficam em transicao.
    short_penalty = 0.10 if token_count < 4 and technical_count == 0 else 0.0

    # Soma final dos sinais positivos menos penalidades.
    score = (
        base
        + length_score
        + technical_score
        + cohesion_score
        + command_score
        + structure_score
        + short_technical_rescue
        + dense_domain_bonus
        - short_penalty
        - gibberish_score * 0.55
    )

    # Garante contrato de retorno em 0..1.
    return clamp01(score)


def estimate_S_raw(text: str) -> float:
    """Calcula entropia simples de caracteres como diagnostico."""

    if not text:
        return 0.0

    # Conta frequencia de cada caractere.
    counts = Counter(text)
    total = len(text)
    entropy = 0.0

    # Entropia de Shannon: soma -p*log2(p).
    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log2(probability)
    return entropy


def estimate_F_flow_raw(text: str) -> float:
    """Estima fluxo/estrutura do prompt em escala aproximada 0..2.5."""

    tokens = normalized_tokens(text)
    if not tokens:
        return 0.0

    # Medidas base para fluxo.
    token_count = len(tokens)
    normalized = normalize_text(text)
    technical_count = count_technical_terms(text)

    # Textos maiores tendem a carregar mais contexto, com saturacao.
    length_score = min(0.65, math.log1p(token_count) / math.log1p(200) * 0.70)

    # Pontuacao util indica estrutura: pergunta, enumeracao, atribuicao, etc.
    useful_punctuation = sum(1 for char in text if char in ".:;?=%\n")
    punctuation_score = min(0.35, useful_punctuation / max(1, token_count) * 0.22)

    # Estrutura explicita do texto.
    structure_score = 0.0
    if _has_any(normalized, {"primeiro", "segundo", "depois", "entao", "finalmente", "por fim"}):
        structure_score += 0.25
    if ":" in text:
        structure_score += 0.15
    if re.search(r"(^|\n)\s*[-*0-9]+[.)-]?\s+", text):
        structure_score += 0.10
    if len(re.findall(r"[.!?]", text)) >= 2:
        structure_score += 0.10
    structure_score = min(0.45, structure_score)

    # Termos tecnicos aumentam a estimativa de fluxo especializado.
    technical_score = min(0.70, technical_count * 0.13)

    # Verbos de tarefa analitica indicam fluxo de trabalho mais claro.
    intent_score = 0.18 if _has_any(
        normalized,
        {"critica", "derive", "explique", "explica", "monte", "modelo"},
    ) else 0.0

    # F_flow_raw e limitado em 2.5; o roteador normaliza dividindo por 2.5.
    return min(2.5, length_score + punctuation_score + structure_score + technical_score + intent_score)


def compute_C_llm(I: float, S_norm: float, F_flow_norm: float, M: float, tier: str) -> float:
    """Aplica a formula canonica C_llm para o tier escolhido."""

    # Primeiro traduzimos o tier operacional para perfil de coeficientes.
    profile_name = ROUTE_TO_COEFFICIENT_PROFILE.get(tier, tier)

    # Se vier um tier desconhecido, usamos o perfil local padrao LLM denso.
    coefficients = COEFFICIENTS.get(profile_name, COEFFICIENTS["LLM denso"])

    # M so entra no deep+/raciocinio, como pedido na especificacao.
    epsilon = 0.90 if tier == "deep+" or profile_name == "LLM raciocinio" else 0.0

    # Formula: alpha*I - beta*S_norm + delta*F_flow_norm + epsilon*M.
    return (
        coefficients["alpha"] * I
        - coefficients["beta"] * S_norm
        + coefficients["delta"] * F_flow_norm
        + epsilon * M
    )
