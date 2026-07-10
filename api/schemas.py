"""Esquemas Pydantic da API (primeira linha de guardrail: valida a entrada)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from ml.preprocess import CATEGORICAL_CHOICES


class CustomerProfile(BaseModel):
    """Perfil de cliente no esquema do Telco Churn. Restringe categorias a valores válidos."""

    gender: Literal["Female", "Male"]
    SeniorCitizen: int = Field(ge=0, le=1)
    Partner: Literal["Yes", "No"]
    Dependents: Literal["Yes", "No"]
    tenure: float = Field(ge=0, le=100, description="Meses como cliente")
    PhoneService: Literal["Yes", "No"]
    MultipleLines: Literal["Yes", "No", "No phone service"]
    InternetService: Literal["DSL", "Fiber optic", "No"]
    OnlineSecurity: Literal["Yes", "No", "No internet service"]
    OnlineBackup: Literal["Yes", "No", "No internet service"]
    DeviceProtection: Literal["Yes", "No", "No internet service"]
    TechSupport: Literal["Yes", "No", "No internet service"]
    StreamingTV: Literal["Yes", "No", "No internet service"]
    StreamingMovies: Literal["Yes", "No", "No internet service"]
    Contract: Literal["Month-to-month", "One year", "Two year"]
    PaperlessBilling: Literal["Yes", "No"]
    PaymentMethod: Literal[
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ]
    MonthlyCharges: float = Field(ge=0, le=1000)
    TotalCharges: float = Field(ge=0, le=100000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "gender": "Female",
                "SeniorCitizen": 0,
                "Partner": "No",
                "Dependents": "No",
                "tenure": 2,
                "PhoneService": "Yes",
                "MultipleLines": "No",
                "InternetService": "Fiber optic",
                "OnlineSecurity": "No",
                "OnlineBackup": "No",
                "DeviceProtection": "No",
                "TechSupport": "No",
                "StreamingTV": "Yes",
                "StreamingMovies": "Yes",
                "Contract": "Month-to-month",
                "PaperlessBilling": "Yes",
                "PaymentMethod": "Electronic check",
                "MonthlyCharges": 95.0,
                "TotalCharges": 190.0,
            }
        }
    }


class ChatRequest(BaseModel):
    """Requisição do chat de retenção: perfil do cliente + pergunta livre."""

    customer: CustomerProfile
    message: Optional[str] = Field(default=None, max_length=2000)


class Factor(BaseModel):
    feature: str
    label: str
    value: object | None = None
    contribution: float
    direction: str


class AgentMeta(BaseModel):
    trace_id: str
    latency_ms: float
    fallback: bool
    fallback_reason: Optional[str] = None
    guardrail_blocked: bool = False
    guardrail_reason: Optional[str] = None
    tools_used: list[str] = []
    cost_usd: float = 0.0
    model: Optional[str] = None


class AgentResponse(BaseModel):
    """Resposta padrão do agente para /predict e /chat."""

    answer: str
    churn_probability: Optional[float] = None
    churn_probability_pct: Optional[float] = None
    risk_band: Optional[str] = None
    will_churn: Optional[bool] = None
    factors: list[Factor] = []
    meta: AgentMeta


# Exposto para debug/documentação: valores válidos por campo categórico.
CATEGORICAL_OPTIONS = CATEGORICAL_CHOICES
