"""Pré-processamento do Telco Customer Churn.

Fonte única de verdade das features do problema: os módulos de treino, explicação,
API (schemas) e produto (Streamlit) importam daqui para não divergirem.
"""
from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# ---------------------------------------------------------------------------
# Definição das features (canônica)
# ---------------------------------------------------------------------------
TARGET = "Churn"
ID_COLUMN = "customerID"

# SeniorCitizen já vem 0/1 no dataset -> tratamos como numérico.
NUMERIC_FEATURES = ["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"]

CATEGORICAL_FEATURES = [
    "gender",
    "Partner",
    "Dependents",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
]

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Valores válidos por feature categórica (usado por guardrails/validação de entrada).
CATEGORICAL_CHOICES: dict[str, list[str]] = {
    "gender": ["Female", "Male"],
    "Partner": ["Yes", "No"],
    "Dependents": ["Yes", "No"],
    "PhoneService": ["Yes", "No"],
    "MultipleLines": ["Yes", "No", "No phone service"],
    "InternetService": ["DSL", "Fiber optic", "No"],
    "OnlineSecurity": ["Yes", "No", "No internet service"],
    "OnlineBackup": ["Yes", "No", "No internet service"],
    "DeviceProtection": ["Yes", "No", "No internet service"],
    "TechSupport": ["Yes", "No", "No internet service"],
    "StreamingTV": ["Yes", "No", "No internet service"],
    "StreamingMovies": ["Yes", "No", "No internet service"],
    "Contract": ["Month-to-month", "One year", "Two year"],
    "PaperlessBilling": ["Yes", "No"],
    "PaymentMethod": [
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ],
}

# Rótulos legíveis em PT para as features (usado nas explicações e no produto).
FEATURE_LABELS_PT: dict[str, str] = {
    "SeniorCitizen": "Idoso (65+)",
    "tenure": "Tempo de casa (meses)",
    "MonthlyCharges": "Cobrança mensal",
    "TotalCharges": "Cobrança total acumulada",
    "gender": "Gênero",
    "Partner": "Tem parceiro(a)",
    "Dependents": "Tem dependentes",
    "PhoneService": "Serviço de telefone",
    "MultipleLines": "Múltiplas linhas",
    "InternetService": "Serviço de internet",
    "OnlineSecurity": "Segurança online",
    "OnlineBackup": "Backup online",
    "DeviceProtection": "Proteção de dispositivo",
    "TechSupport": "Suporte técnico",
    "StreamingTV": "Streaming de TV",
    "StreamingMovies": "Streaming de filmes",
    "Contract": "Tipo de contrato",
    "PaperlessBilling": "Fatura digital",
    "PaymentMethod": "Forma de pagamento",
}


def load_raw(csv_path: str) -> pd.DataFrame:
    """Carrega o CSV bruto do Telco Churn."""
    return pd.read_csv(csv_path)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Limpeza mínima e determinística.

    - `TotalCharges` vem como texto e tem ~11 células em branco (clientes com
      tenure=0, recém-chegados). Convertemos para número e preenchemos com 0.0.
    - Garante que as colunas numéricas são float.
    """
    df = df.copy()
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    # Blanks == clientes novos (tenure 0) -> ainda não acumularam cobrança.
    df["TotalCharges"] = df["TotalCharges"].fillna(0.0)
    for col in NUMERIC_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def split_features_target(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Separa X (features canônicas) e y (Churn -> 1/0)."""
    X = df[FEATURE_COLUMNS].copy()
    y = (df[TARGET].astype(str).str.strip() == "Yes").astype(int)
    return X, y


def build_preprocessor() -> ColumnTransformer:
    """ColumnTransformer: OneHot nas categóricas + escala nas numéricas.

    `handle_unknown="ignore"` garante robustez se aparecer uma categoria não vista
    em produção (guardrail extra além da validação de entrada).
    """
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )


def original_feature_of(transformed_name: str) -> str:
    """Mapeia um nome de coluna transformada de volta à feature original.

    Ex.: "num__tenure" -> "tenure"; "cat__Contract_Two year" -> "Contract".
    Usado para agregar contribuições SHAP por feature de negócio.
    """
    name = transformed_name
    if name.startswith("num__"):
        return name[len("num__"):]
    if name.startswith("cat__"):
        rest = name[len("cat__"):]
        # Encontra o prefixo que casa com uma feature categórica conhecida.
        for feat in CATEGORICAL_FEATURES:
            if rest == feat or rest.startswith(feat + "_"):
                return feat
    return name
