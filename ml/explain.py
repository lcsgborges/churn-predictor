"""Explicação por cliente: quais fatores puxam o risco de churn para cima/baixo.

Usa SHAP (TreeExplainer) sobre o classificador do pipeline e agrega as contribuições
das colunas one-hot de volta à feature de negócio original. Se o SHAP falhar por
qualquer motivo, degrada para importância global do modelo (nunca quebra a resposta).
"""
from __future__ import annotations

import functools

import numpy as np

from ml.model import customer_to_frame, load_bundle
from ml.preprocess import FEATURE_LABELS_PT, original_feature_of


@functools.lru_cache(maxsize=1)
def _explainer():
    """Cria (uma vez) o TreeExplainer sobre o classificador treinado."""
    import shap

    bundle = load_bundle()
    clf = bundle["pipeline"].named_steps["clf"]
    return shap.TreeExplainer(clf)


def _aggregate_by_feature(shap_row: np.ndarray, feature_names: list[str]) -> dict[str, float]:
    """Soma as contribuições SHAP das colunas transformadas por feature original."""
    agg: dict[str, float] = {}
    for name, value in zip(feature_names, shap_row):
        orig = original_feature_of(name)
        agg[orig] = agg.get(orig, 0.0) + float(value)
    return agg


def explain_one(customer: dict, top_n: int = 5) -> dict:
    """Retorna os principais fatores de risco/proteção para um cliente.

    Estrutura de retorno:
        {
          "method": "shap" | "global_importance",
          "factors": [
             {"feature","label","value","contribution","direction"}  # ordenado por |contrib|
          ]
        }
    `direction`: "aumenta" (empurra p/ churn) ou "reduz" (protege).
    """
    bundle = load_bundle()
    prep = bundle["pipeline"].named_steps["prep"]
    feature_names = bundle["feature_names_out"]
    frame = customer_to_frame(customer)

    try:
        X_trans = prep.transform(frame)
        explainer = _explainer()
        shap_values = explainer.shap_values(X_trans)
        # Binário: pode vir (n, k) ou lista por classe -> pega a classe positiva.
        if isinstance(shap_values, list):
            shap_values = shap_values[-1]
        shap_values = np.asarray(shap_values)
        if shap_values.ndim == 3:  # (n, k, classes)
            shap_values = shap_values[:, :, -1]
        agg = _aggregate_by_feature(shap_values[0], feature_names)
        method = "shap"
    except Exception:
        # Fallback: importância global do modelo (sem direção por instância).
        agg = _global_importance(bundle, feature_names)
        method = "global_importance"

    ordered = sorted(agg.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_n]
    factors = []
    for feat, contrib in ordered:
        factors.append(
            {
                "feature": feat,
                "label": FEATURE_LABELS_PT.get(feat, feat),
                "value": customer.get(feat),
                "contribution": round(float(contrib), 4),
                "direction": "aumenta" if contrib > 0 else "reduz",
            }
        )
    return {"method": method, "factors": factors}


def _global_importance(bundle: dict, feature_names: list[str]) -> dict[str, float]:
    clf = bundle["pipeline"].named_steps["clf"]
    importances = getattr(clf, "feature_importances_", None)
    if importances is None:
        coef = getattr(clf, "coef_", np.zeros((1, len(feature_names))))
        importances = np.abs(coef).ravel()
    return _aggregate_by_feature(np.asarray(importances), feature_names)
