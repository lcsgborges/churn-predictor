"""Metadados do formulário do produto (fonte única para renderizar a UI).

O modelo foi treinado com os valores em inglês do dataset Telco; por isso os
*valores* enviados à API continuam em inglês e só os *rótulos* são traduzidos.
"""
from __future__ import annotations

DOCS_URL = "https://lcsgborges.github.io/churn-predictor/"

# Valor (inglês, enviado à API) -> rótulo em português (exibição).
VALUE_LABELS = {
    "Female": "Feminino",
    "Male": "Masculino",
    "Yes": "Sim",
    "No": "Não",
    "No phone service": "Sem serviço de telefone",
    "No internet service": "Sem internet",
    "Fiber optic": "Fibra óptica",
    "DSL": "DSL",
    "Month-to-month": "Mensal",
    "One year": "Anual",
    "Two year": "2 anos",
    "Electronic check": "Cheque eletrônico",
    "Mailed check": "Cheque por correio",
    "Bank transfer (automatic)": "Transferência bancária (automática)",
    "Credit card (automatic)": "Cartão de crédito (automático)",
}


def _select(name: str, label: str, options: list[str]) -> dict:
    return {
        "name": name,
        "label": label,
        "kind": "select",
        "options": [{"value": o, "label": VALUE_LABELS.get(o, o)} for o in options],
    }


# Campos principais (sempre visíveis), na ordem de exibição.
MAIN_FIELDS = [
    _select("gender", "Gênero", ["Female", "Male"]),
    {"name": "SeniorCitizen", "label": "Idoso (65+)", "kind": "bool"},
    _select("Partner", "Tem parceiro(a)", ["Yes", "No"]),
    _select("Dependents", "Tem dependentes", ["Yes", "No"]),
    {"name": "tenure", "label": "Tempo de casa (meses)", "kind": "int", "min": 0, "max": 72, "step": 1},
    _select("Contract", "Contrato", ["Month-to-month", "One year", "Two year"]),
    _select("InternetService", "Internet", ["Fiber optic", "DSL", "No"]),
    _select(
        "PaymentMethod",
        "Pagamento",
        ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"],
    ),
    {"name": "MonthlyCharges", "label": "Cobrança mensal", "kind": "float", "min": 0, "max": 200, "step": 0.5},
    {"name": "TotalCharges", "label": "Cobrança total", "kind": "float", "min": 0, "max": 9000, "step": 10},
]

# Campos avançados (dentro de um "accordion").
ADVANCED_FIELDS = [
    _select("PhoneService", "Serviço de telefone", ["Yes", "No"]),
    _select("MultipleLines", "Múltiplas linhas", ["No", "Yes", "No phone service"]),
    _select("OnlineSecurity", "Segurança online", ["No", "Yes", "No internet service"]),
    _select("OnlineBackup", "Backup online", ["No", "Yes", "No internet service"]),
    _select("DeviceProtection", "Proteção de dispositivo", ["No", "Yes", "No internet service"]),
    _select("TechSupport", "Suporte técnico", ["No", "Yes", "No internet service"]),
    _select("StreamingTV", "Streaming de TV", ["No", "Yes", "No internet service"]),
    _select("StreamingMovies", "Streaming de filmes", ["No", "Yes", "No internet service"]),
    _select("PaperlessBilling", "Fatura digital (sem papel)", ["Yes", "No"]),
]

# Presets prontos (mesmos perfis usados nos testes) — preenchem o formulário.
PRESETS = {
    "alto": {
        "gender": "Female", "SeniorCitizen": 0, "Partner": "No", "Dependents": "No",
        "tenure": 2, "PhoneService": "Yes", "MultipleLines": "No", "InternetService": "Fiber optic",
        "OnlineSecurity": "No", "OnlineBackup": "No", "DeviceProtection": "No", "TechSupport": "No",
        "StreamingTV": "Yes", "StreamingMovies": "Yes", "Contract": "Month-to-month",
        "PaperlessBilling": "Yes", "PaymentMethod": "Electronic check",
        "MonthlyCharges": 95.0, "TotalCharges": 190.0,
    },
    "baixo": {
        "gender": "Male", "SeniorCitizen": 0, "Partner": "Yes", "Dependents": "Yes",
        "tenure": 60, "PhoneService": "Yes", "MultipleLines": "Yes", "InternetService": "DSL",
        "OnlineSecurity": "Yes", "OnlineBackup": "Yes", "DeviceProtection": "Yes", "TechSupport": "Yes",
        "StreamingTV": "No", "StreamingMovies": "No", "Contract": "Two year",
        "PaperlessBilling": "No", "PaymentMethod": "Credit card (automatic)",
        "MonthlyCharges": 45.0, "TotalCharges": 2700.0,
    },
}
