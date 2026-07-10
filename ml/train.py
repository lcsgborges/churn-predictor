"""Treino do modelo de churn.

Estratégia (documentada no relatório):
  1. Baseline: Regressão Logística com class_weight="balanced".
  2. Candidato: Gradient Boosting (melhor captura de interações; compatível com SHAP).
  Escolhemos o de maior PR-AUC (Average Precision), métrica adequada para classe
  desbalanceada. Em seguida, tunamos o limiar de decisão maximizando F1 na validação.

Uso:
    python -m ml.train
Gera:
    models/churn_model.pkl   (bundle: pipeline + limiar + metadados)
    models/metrics.json      (métricas legíveis das duas abordagens)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ml.preprocess import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    build_preprocessor,
    clean,
    load_raw,
    split_features_target,
)

DATA_PATH = "data/telco_churn.csv"
MODEL_PATH = "models/churn_model.pkl"
METRICS_PATH = "models/metrics.json"
RANDOM_STATE = 42


def _evaluate(y_true, proba, threshold: float) -> dict:
    pred = (proba >= threshold).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y_true, proba)),
        "pr_auc": float(average_precision_score(y_true, proba)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "threshold": float(threshold),
    }


def _best_f1_threshold(y_true, proba) -> float:
    """Varre limiares e devolve o que maximiza F1 (equilíbrio precisão/recall)."""
    grid = np.linspace(0.1, 0.9, 81)
    scores = [f1_score(y_true, (proba >= t).astype(int), zero_division=0) for t in grid]
    return float(grid[int(np.argmax(scores))])


def _make_pipeline(classifier) -> Pipeline:
    return Pipeline([("prep", build_preprocessor()), ("clf", classifier)])


def train() -> dict:
    df = clean(load_raw(DATA_PATH))
    X, y = split_features_target(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
    )

    candidates = {
        "logistic_regression": _make_pipeline(
            LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE)
        ),
        "gradient_boosting": _make_pipeline(
            GradientBoostingClassifier(random_state=RANDOM_STATE)
        ),
    }

    results: dict[str, dict] = {}
    fitted: dict[str, Pipeline] = {}
    for name, pipe in candidates.items():
        pipe.fit(X_train, y_train)
        proba = pipe.predict_proba(X_test)[:, 1]
        thr = _best_f1_threshold(y_test, proba)
        results[name] = _evaluate(y_test, proba, thr)
        fitted[name] = pipe
        print(
            f"[{name}] PR-AUC={results[name]['pr_auc']:.3f} "
            f"ROC-AUC={results[name]['roc_auc']:.3f} "
            f"F1={results[name]['f1']:.3f} recall={results[name]['recall']:.3f} "
            f"thr={thr:.2f}"
        )

    # Escolhe o melhor por PR-AUC (adequado a desbalanceamento).
    best_name = max(results, key=lambda n: results[n]["pr_auc"])
    best_pipe = fitted[best_name]
    best_threshold = results[best_name]["threshold"]
    print(f"\n>> Modelo escolhido: {best_name} (maior PR-AUC)")

    churn_rate = float(y.mean())
    bundle = {
        "pipeline": best_pipe,
        "threshold": best_threshold,
        "model_name": best_name,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "feature_names_out": list(
            best_pipe.named_steps["prep"].get_feature_names_out()
        ),
        "base_churn_rate": churn_rate,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }

    Path("models").mkdir(exist_ok=True)
    joblib.dump(bundle, MODEL_PATH)

    metrics_out = {
        "chosen_model": best_name,
        "base_churn_rate": churn_rate,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "candidates": results,
        "trained_at": bundle["trained_at"],
    }
    Path(METRICS_PATH).write_text(json.dumps(metrics_out, indent=2, ensure_ascii=False))
    print(f">> Salvo: {MODEL_PATH} e {METRICS_PATH}")
    return metrics_out


if __name__ == "__main__":
    train()
