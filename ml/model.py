"""Carregamento do modelo e predição de churn para um cliente.

Encapsula o bundle salvo por `ml.train` para que agente, API e testes usem a mesma
lógica de predição (fonte única de verdade de inferência).
"""
from __future__ import annotations

import functools
from pathlib import Path

import joblib
import pandas as pd

from ml.preprocess import FEATURE_COLUMNS

MODEL_PATH = "models/churn_model.pkl"


class ModelNotTrainedError(RuntimeError):
    """Levantado quando o modelo ainda não foi treinado (arquivo ausente)."""


@functools.lru_cache(maxsize=1)
def load_bundle(path: str = MODEL_PATH) -> dict:
    """Carrega o bundle treinado (cacheado). Retreine com `python -m ml.train`."""
    if not Path(path).exists():
        raise ModelNotTrainedError(
            f"Modelo não encontrado em '{path}'. Rode: python -m ml.train"
        )
    return joblib.load(path)


def customer_to_frame(customer: dict) -> pd.DataFrame:
    """Converte um dict de perfil de cliente em DataFrame de 1 linha, na ordem canônica.

    Campos ausentes viram NA e são tratados pelo pré-processador do pipeline.
    """
    row = {col: customer.get(col) for col in FEATURE_COLUMNS}
    return pd.DataFrame([row], columns=FEATURE_COLUMNS)


def predict_one(customer: dict) -> dict:
    """Prediz churn para um cliente.

    Retorna: probabilidade [0,1], rótulo binário segundo o limiar tunado, o limiar
    usado e a taxa-base de churn (referência para o agente calibrar o discurso).
    """
    bundle = load_bundle()
    frame = customer_to_frame(customer)
    proba = float(bundle["pipeline"].predict_proba(frame)[:, 1][0])
    threshold = float(bundle["threshold"])
    return {
        "churn_probability": proba,
        "will_churn": bool(proba >= threshold),
        "threshold": threshold,
        "base_churn_rate": float(bundle.get("base_churn_rate", 0.265)),
        "model_name": bundle.get("model_name", "unknown"),
    }
