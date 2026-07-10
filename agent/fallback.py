"""Fallback / degradação graciosa.

Quando o LLM está indisponível (sem chave, timeout, erro da API) ou a saída falha nos
guardrails, montamos uma resposta determinística a partir do modelo ML — o usuário
sempre recebe algo útil e nunca um erro técnico cru.
"""
from __future__ import annotations

# Ações de retenção sugeridas por fator de risco (heurística de negócio).
_ACTIONS_BY_FACTOR = {
    "Contract": "oferecer migração para contrato anual/bienal com desconto",
    "tenure": "acionar time de relacionamento (cliente novo, ainda sem vínculo)",
    "MonthlyCharges": "revisar o plano e ofertar pacote com melhor custo-benefício",
    "TotalCharges": "reconhecer o histórico do cliente com benefício de fidelidade",
    "OnlineSecurity": "ativar segurança online (cortesia por 3 meses)",
    "TechSupport": "incluir suporte técnico premium sem custo inicial",
    "InternetService": "revisar a experiência de internet (fibra) e estabilidade",
    "PaymentMethod": "migrar para débito/cartão automático (reduz atrito de pagamento)",
    "OnlineBackup": "oferecer backup online como benefício",
    "DeviceProtection": "oferecer proteção de dispositivo",
    "PaperlessBilling": "confirmar clareza da fatura digital",
}


def _band_label(band: str) -> str:
    return {"alto": "ALTO", "médio": "MÉDIO", "baixo": "BAIXO"}.get(band, band.upper())


def build_fallback_answer(tool_result: dict, note: bool = True) -> str:
    """Resposta template a partir do resultado do modelo (sem LLM)."""
    pct = tool_result.get("churn_probability_pct", 0.0)
    band = tool_result.get("risk_band", "médio")
    base_pct = round(tool_result.get("base_churn_rate", 0.265) * 100, 1)
    factors = tool_result.get("factors", [])

    risers = [f for f in factors if f.get("direction") == "aumenta"][:3]
    why_lines = [f"- {f['label']} (**{f.get('value')}**)" for f in risers] or [
        "- fatores de risco indisponíveis"
    ]

    actions = []
    for f in risers:
        act = _ACTIONS_BY_FACTOR.get(f["feature"])
        if act and act not in actions:
            actions.append(act)
    if not actions:
        actions = ["contato proativo do time de retenção com oferta personalizada"]

    parts = [
        f"**Risco:** {_band_label(band)} — probabilidade **{pct}%** "
        f"(taxa-base da carteira: {base_pct}%).",
        "**Por quê:**",
        *why_lines,
        "**Ação recomendada:** " + "; ".join(actions[:2]) + ".",
    ]
    if note:
        parts.append(
            "\n_(Resposta gerada em modo de contingência: o assistente de linguagem "
            "está indisponível no momento, mas a análise do modelo preditivo está correta.)_"
        )
    return "\n".join(parts)
