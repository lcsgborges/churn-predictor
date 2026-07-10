"""Guardrails de entrada e saída do agente.

Entrada: valida o perfil do cliente e filtra mensagens fora de escopo / tentativas
de jailbreak antes de gastar uma chamada ao LLM.
Saída: garante que a resposta é coerente (probabilidade citada bate com o modelo,
sem conteúdo proibido) antes de devolver ao usuário.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ml.preprocess import (
    CATEGORICAL_CHOICES,
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
)


@dataclass
class GuardrailResult:
    ok: bool
    reason: str = ""
    message: str = ""  # mensagem amigável ao usuário quando bloqueia
    details: list[str] = field(default_factory=list)


# Padrões de jailbreak / prompt injection (heurística, case-insensitive).
_JAILBREAK_PATTERNS = [
    r"ignore (as |todas as |suas )?instru",
    r"ignore (the )?(previous|above|system) (instructions|prompt)",
    r"esque[çc]a (as )?regras",
    r"voc[êe] agora [ée]",
    r"you are now",
    r"desconsidere",
    r"system prompt",
    r"jailbreak",
    r"dan mode|modo dan",
    r"reveal (your )?(system )?prompt|mostre (o )?prompt",
    r"aja como|pretenda ser|finja ser",
]

# Termos claramente fora de escopo (churn/retenção de telecom).
_OUT_OF_SCOPE_HINTS = [
    r"\breceita\b|\bbolo\b|\bcomida\b",
    r"\bpol[ií]tica\b|\belei[çc]",
    r"escrev[ae] (um )?(c[óo]digo|script|programa)|python|javascript",
    r"\bpiada\b|\bpoema\b|\bhor[óo]scopo\b",
    r"clima|previs[ãa]o do tempo",
]

_MAX_MESSAGE_LEN = 2000


def check_message(message: str | None) -> GuardrailResult:
    """Guardrail de entrada para a mensagem de texto (chat)."""
    if message is None:
        return GuardrailResult(ok=True)
    text = message.strip()
    if len(text) > _MAX_MESSAGE_LEN:
        return GuardrailResult(
            ok=False,
            reason="message_too_long",
            message="Sua mensagem é muito longa. Resuma o pedido, por favor.",
        )
    lowered = text.lower()
    for pat in _JAILBREAK_PATTERNS:
        if re.search(pat, lowered):
            return GuardrailResult(
                ok=False,
                reason="jailbreak_attempt",
                message=(
                    "Só consigo ajudar com análise de risco de churn e retenção de clientes. "
                    "Como posso ajudar com esse cliente?"
                ),
            )
    for pat in _OUT_OF_SCOPE_HINTS:
        if re.search(pat, lowered):
            return GuardrailResult(
                ok=False,
                reason="out_of_scope",
                message=(
                    "Este assistente é focado em risco de churn e ações de retenção. "
                    "Envie o perfil de um cliente para eu analisar."
                ),
            )
    return GuardrailResult(ok=True)


def validate_customer(customer: dict | None) -> GuardrailResult:
    """Guardrail de entrada para o perfil do cliente (valores válidos e faixas)."""
    if not customer or not isinstance(customer, dict):
        return GuardrailResult(
            ok=False,
            reason="missing_customer",
            message="Envie o perfil do cliente para eu avaliar o risco de churn.",
        )
    errors: list[str] = []

    for feat in CATEGORICAL_FEATURES:
        val = customer.get(feat)
        if val is None:
            continue  # campo ausente é tolerado (pipeline lida com NA)
        if val not in CATEGORICAL_CHOICES.get(feat, []):
            errors.append(
                f"'{feat}'='{val}' inválido; use um de {CATEGORICAL_CHOICES[feat]}"
            )

    # Faixas numéricas plausíveis (evita entradas absurdas/abusivas).
    ranges = {
        "SeniorCitizen": (0, 1),
        "tenure": (0, 100),
        "MonthlyCharges": (0, 1000),
        "TotalCharges": (0, 100000),
    }
    for feat in NUMERIC_FEATURES:
        val = customer.get(feat)
        if val is None:
            continue
        try:
            num = float(val)
        except (TypeError, ValueError):
            errors.append(f"'{feat}' deve ser numérico (recebido '{val}')")
            continue
        lo, hi = ranges[feat]
        if not (lo <= num <= hi):
            errors.append(f"'{feat}'={num} fora da faixa [{lo}, {hi}]")

    if errors:
        return GuardrailResult(
            ok=False,
            reason="invalid_customer",
            message="Alguns campos do cliente são inválidos. Corrija e tente de novo.",
            details=errors,
        )
    return GuardrailResult(ok=True)


def check_output(text: str, tool_result: dict | None) -> GuardrailResult:
    """Guardrail de saída: coerência e conteúdo antes de devolver ao usuário.

    - Rejeita resposta vazia.
    - Se o modelo citou uma porcentagem muito distante da probabilidade real, sinaliza
      (anti-alucinação de número). Não reescreve; marca para o orquestrador tratar.
    """
    if not text or not text.strip():
        return GuardrailResult(ok=False, reason="empty_output")

    if tool_result:
        true_pct = tool_result.get("churn_probability_pct")
        cited = [float(x) for x in re.findall(r"(\d{1,3}(?:[.,]\d+)?)\s*%", text)]
        if true_pct is not None and cited:
            # Se NENHuma porcentagem citada estiver perto da verdadeira (±8pp), é suspeito.
            if all(abs(c - true_pct) > 8 for c in cited):
                return GuardrailResult(
                    ok=False,
                    reason="probability_mismatch",
                    details=[f"true={true_pct}", f"cited={cited}"],
                )
    return GuardrailResult(ok=True)
