"""Ferramentas expostas ao agente (function calling).

Hoje há uma ferramenta: `predict_churn`, que embrulha o modelo ML + a explicação SHAP.
É a única fonte da probabilidade e dos fatores de risco — o LLM não pode inventá-los.
"""
from __future__ import annotations

from ml.explain import explain_one
from ml.model import predict_one


def predict_churn(customer: dict, top_n: int = 5) -> dict:
    """Executa a predição + explicação para um cliente e devolve um dict pronto p/ o LLM."""
    pred = predict_one(customer)
    expl = explain_one(customer, top_n=top_n)
    prob = pred["churn_probability"]
    base = pred["base_churn_rate"]
    if prob >= 0.66:
        risk_band = "alto"
    elif prob >= max(base, 0.33):
        risk_band = "médio"
    else:
        risk_band = "baixo"
    return {
        "churn_probability": round(prob, 4),
        "churn_probability_pct": round(prob * 100, 1),
        "risk_band": risk_band,
        "will_churn": pred["will_churn"],
        "threshold": round(pred["threshold"], 4),
        "base_churn_rate": round(base, 4),
        "explanation_method": expl["method"],
        "factors": expl["factors"],
        "model_name": pred["model_name"],
    }


# Esquema da ferramenta no formato de tools da OpenAI (function calling).
PREDICT_CHURN_TOOL = {
    "type": "function",
    "function": {
        "name": "predict_churn",
        "description": (
            "Calcula a probabilidade de churn de um cliente de telecom e os principais "
            "fatores de risco (via modelo de ML + SHAP). Use SEMPRE antes de opinar sobre risco."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "customer": {
                    "type": "object",
                    "description": "Perfil do cliente com as colunas do dataset Telco Churn.",
                }
            },
            "required": ["customer"],
        },
    },
}

TOOLS = [PREDICT_CHURN_TOOL]

# Mapa nome->função para o dispatcher do agente.
TOOL_FUNCTIONS = {"predict_churn": predict_churn}
