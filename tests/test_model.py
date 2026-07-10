"""Smoke tests do modelo e da explicação."""
from ml.explain import explain_one
from ml.model import predict_one


def test_predict_returns_valid_probability(high_risk_customer):
    out = predict_one(high_risk_customer)
    assert 0.0 <= out["churn_probability"] <= 1.0
    assert isinstance(out["will_churn"], bool)
    assert 0.0 < out["threshold"] < 1.0


def test_high_risk_greater_than_low_risk(high_risk_customer, low_risk_customer):
    hi = predict_one(high_risk_customer)["churn_probability"]
    lo = predict_one(low_risk_customer)["churn_probability"]
    assert hi > lo, "cliente de alto risco deveria ter prob maior que o de baixo risco"


def test_explain_returns_factors(high_risk_customer):
    expl = explain_one(high_risk_customer, top_n=5)
    assert expl["method"] in {"shap", "global_importance"}
    assert len(expl["factors"]) == 5
    for f in expl["factors"]:
        assert {"feature", "label", "contribution", "direction"} <= set(f)
        assert f["direction"] in {"aumenta", "reduz"}


def test_contract_is_top_driver_for_high_risk(high_risk_customer):
    # Contrato mensal é o fator dominante de churn no Telco -> deve aparecer no topo.
    factors = explain_one(high_risk_customer, top_n=3)["factors"]
    assert any(f["feature"] == "Contract" for f in factors)
