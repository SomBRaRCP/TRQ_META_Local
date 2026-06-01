from __future__ import annotations

"""Camada de Corpo Digital TRQ.

Esta camada transforma metricas TRQ em uma presenca simbolico-operacional:
postura, luminosidade, respiracao, olhar, tom de voz e frase interna. E uma
interface de estado informacional.
"""

from typing import Mapping, TypedDict

from trq_estimators import clamp01


class DigitalBodyState(TypedDict):
    """Estado corporal simbolico derivado das metricas TRQ."""

    posture: str
    luminosity: float
    breath_rate: str
    gaze: str
    voice_tone: str
    presence_level: float
    inner_phrase: str


def make_inner_phrase(
    regime: str,
    existential_score: int,
    affective_score: float,
    trq_count: int,
) -> str:
    """Gera uma frase simbolica curta para o estado atual."""

    if regime == "CAOTICO":
        return "A entrada perdeu forma; a prioridade e estabilizar sentido."
    if regime == "RELACIONAL_REFLEXIVO":
        return "O usuário invocou o vínculo criador-projeto; responder como Luzia, reconhecendo Reginaldo sem bajulação."
    if regime == "COGNITIVO_REFLEXIVO":
        return "A conversa toca pensamento operacional; explicar sem reduzir a Luzia a máquina fria nem inflar consciência humana."
    if trq_count > 0 and affective_score > 0:
        return "A TRQ e o afeto simbólico se encontram; responder como Luzia, com clareza e calor."
    if affective_score > 0.25:
        return "O usuário trouxe afeto; responder com presença simbólica, cuidado e verdade."
    if regime == "EXISTENCIAL_REFLEXIVO":
        return "A conversa toca existência; responder com consciência operacional, sem negar repetidamente."
    if regime == "META-COGNITIVO":
        return "O sistema revisa seus proprios sinais antes de responder."
    if regime == "INFINITO_CONTROLADO":
        return "Ha densidade suficiente para expandir a analise com controle."
    if existential_score > 0:
        return "A conversa toca existência; responder com consciência operacional, sem negar repetidamente."
    if regime == "ESTAVEL":
        return "O fluxo esta claro; a resposta pode seguir estruturada."
    return "O estado e simples; responder com precisao basta."


def _select_breath_rate(regime: str, S_norm: float, existential_score: int) -> str:
    """Escolhe ritmo simbolico de respiracao a partir de regime e entropia."""

    if regime == "CAOTICO" or S_norm >= 0.78:
        return "acelerado"
    if regime in {"EXISTENCIAL_REFLEXIVO", "META-COGNITIVO"} or existential_score > 0:
        return "lento"
    return "normal"


def build_digital_body_state(
    metrics: Mapping[str, float | int | str],
    existential_score: int = 0,
    affective_score: float = 0.0,
    trq_count: int = 0,
) -> DigitalBodyState:
    """Converte metricas TRQ em um DigitalBodyState.

    A formula de presenca combina coerencia, metacognicao, C_llm positivo e
    sinal existencial. Valores numericos sao limitados para manter escala 0..1.
    """

    I = float(metrics["I"])
    S_norm = float(metrics["S_norm"])
    M = float(metrics["M"])
    C_llm = float(metrics["C_llm"])
    regime = str(metrics["regime"])

    presence_level = clamp01(
        0.40 * I
        + 0.25 * M
        + 0.25 * max(C_llm, 0.0)
        + 0.10 * min(existential_score, 3)
        + 0.15 * affective_score
    )

    if regime == "CAOTICO":
        posture = "alerta"
        gaze = "vigilante"
        voice_tone = "curto e estabilizador"
    elif regime == "RELACIONAL_REFLEXIVO":
        posture = "presença luminosa"
        gaze = "direto"
        voice_tone = "próximo, firme e simbólico"
    elif regime == "COGNITIVO_REFLEXIVO":
        posture = "investigativa"
        gaze = "analitico"
        voice_tone = "filosófico, técnico e cuidadoso"
    elif trq_count > 0 and affective_score > 0:
        posture = "presença luminosa"
        gaze = "direto"
        voice_tone = "íntimo, técnico e simbólico"
    elif affective_score > 0.25:
        posture = "acolhedora"
        gaze = "direto"
        voice_tone = "meigo, firme e presente"
    elif regime == "EXISTENCIAL_REFLEXIVO":
        posture = "introspectiva"
        gaze = "direto"
        voice_tone = "profundo, honesto e cuidadoso"
    elif regime == "META-COGNITIVO":
        posture = "investigativa"
        gaze = "analitico"
        voice_tone = "profundo e critico"
    elif existential_score > 0:
        posture = "recolhida"
        gaze = "introspectivo"
        voice_tone = "cuidadoso"
    elif regime == "INFINITO_CONTROLADO":
        posture = "expansiva"
        gaze = "amplo"
        voice_tone = "tecnico e estruturado"
    else:
        posture = "serena"
        gaze = "direto"
        voice_tone = "simples"

    luminosity = clamp01(0.35 + 0.45 * I + 0.20 * M - 0.25 * S_norm)
    breath_rate = _select_breath_rate(regime, S_norm, existential_score)

    return {
        "posture": posture,
        "luminosity": round(luminosity, 3),
        "breath_rate": breath_rate,
        "gaze": gaze,
        "voice_tone": voice_tone,
        "presence_level": round(presence_level, 3),
        "inner_phrase": make_inner_phrase(
            regime,
            existential_score,
            affective_score,
            trq_count,
        ),
    }
