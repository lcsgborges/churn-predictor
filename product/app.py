"""Produto — painel de retenção (Streamlit).

Consome a API do agente. Três abas:
  - Análise: formulário do perfil do cliente -> risco + fatores + ação.
  - Chat de retenção: conversa sobre o cliente carregado.
  - Monitoramento: latência, custo, taxa de fallback e guardrails (lê /metrics da API).
"""
from __future__ import annotations

import os

import plotly.graph_objects as go
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 60

CHOICES = {
    "gender": ["Female", "Male"],
    "Partner": ["Yes", "No"],
    "Dependents": ["Yes", "No"],
    "PhoneService": ["Yes", "No"],
    "MultipleLines": ["No", "Yes", "No phone service"],
    "InternetService": ["Fiber optic", "DSL", "No"],
    "OnlineSecurity": ["No", "Yes", "No internet service"],
    "OnlineBackup": ["No", "Yes", "No internet service"],
    "DeviceProtection": ["No", "Yes", "No internet service"],
    "TechSupport": ["No", "Yes", "No internet service"],
    "StreamingTV": ["No", "Yes", "No internet service"],
    "StreamingMovies": ["No", "Yes", "No internet service"],
    "Contract": ["Month-to-month", "One year", "Two year"],
    "PaperlessBilling": ["Yes", "No"],
    "PaymentMethod": [
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ],
}

st.set_page_config(page_title="ChurnPredictor", page_icon=":material/trending_down:", layout="wide")


def api_post(path: str, payload: dict) -> dict | None:
    try:
        resp = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 422:
            st.error("Perfil inválido — revise os campos do cliente.")
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        st.error(f"Não foi possível falar com a API ({API_BASE_URL}). Detalhe: {exc}")
        return None


def api_get(path: str) -> dict | None:
    try:
        resp = requests.get(f"{API_BASE_URL}{path}", timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def gauge(pct: float) -> go.Figure:
    color = "#d62728" if pct >= 66 else ("#ff7f0e" if pct >= 33 else "#2ca02c")
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=pct,
            number={"suffix": "%"},
            title={"text": "Probabilidade de churn"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 33], "color": "#e8f5e9"},
                    {"range": [33, 66], "color": "#fff3e0"},
                    {"range": [66, 100], "color": "#ffebee"},
                ],
            },
        )
    )
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=50, b=10))
    return fig


def factors_chart(factors: list[dict]) -> go.Figure:
    factors = list(reversed(factors))
    labels = [f"{f['label']}" for f in factors]
    vals = [f["contribution"] for f in factors]
    colors = ["#d62728" if v > 0 else "#2ca02c" for v in vals]
    fig = go.Figure(go.Bar(x=vals, y=labels, orientation="h", marker_color=colors))
    fig.update_layout(
        title="Fatores de risco (SHAP) — vermelho aumenta, verde reduz",
        height=300,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title="Contribuição para o risco",
    )
    return fig


def customer_form() -> dict:
    st.sidebar.header("Perfil do cliente")
    preset = st.sidebar.selectbox(
        "Carregar exemplo",
        ["Alto risco", "Baixo risco", "Personalizado"],
    )
    high = preset == "Alto risco"
    c: dict = {}
    with st.sidebar:
        c["gender"] = st.selectbox("Gênero", CHOICES["gender"])
        c["SeniorCitizen"] = 1 if st.checkbox("Idoso (65+)", value=False) else 0
        c["Partner"] = st.selectbox("Tem parceiro(a)", CHOICES["Partner"], index=1 if high else 0)
        c["Dependents"] = st.selectbox("Tem dependentes", CHOICES["Dependents"], index=1 if high else 0)
        c["tenure"] = st.slider("Tempo de casa (meses)", 0, 72, 2 if high else 48)
        c["Contract"] = st.selectbox("Contrato", CHOICES["Contract"], index=0 if high else 2)
        c["InternetService"] = st.selectbox("Internet", CHOICES["InternetService"], index=0 if high else 1)
        c["PaymentMethod"] = st.selectbox("Pagamento", CHOICES["PaymentMethod"], index=0 if high else 3)
        c["MonthlyCharges"] = st.slider("Cobrança mensal", 0.0, 200.0, 95.0 if high else 45.0)
        c["TotalCharges"] = st.slider("Cobrança total", 0.0, 9000.0, 190.0 if high else 2200.0)
        with st.expander("Serviços e opções avançadas"):
            for key in [
                "PhoneService", "MultipleLines", "OnlineSecurity", "OnlineBackup",
                "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
                "PaperlessBilling",
            ]:
                c[key] = st.selectbox(key, CHOICES[key])
    return c


def render_result(data: dict):
    col1, col2 = st.columns([1, 1.3])
    with col1:
        st.plotly_chart(gauge(data.get("churn_probability_pct") or 0), use_container_width=True)
    with col2:
        if data.get("factors"):
            st.plotly_chart(factors_chart(data["factors"]), use_container_width=True)
    st.markdown("### Recomendação do agente")
    st.markdown(data["answer"])
    meta = data.get("meta", {})
    tag = (
        ":material/warning: modo contingência (fallback)"
        if meta.get("fallback")
        else ":material/check_circle: agente LLM"
    )
    st.caption(
        f"{tag} · latência {meta.get('latency_ms')} ms · custo ${meta.get('cost_usd', 0):.5f} "
        f"· trace {meta.get('trace_id')}"
    )


def tab_analise(customer: dict):
    st.subheader("Análise de risco de churn")
    if st.button("Analisar cliente", type="primary"):
        with st.spinner("Consultando o agente..."):
            data = api_post("/predict", customer)
        if data:
            st.session_state["last_prediction"] = data
    if "last_prediction" in st.session_state:
        render_result(st.session_state["last_prediction"])
    else:
        st.info("Preencha o perfil na barra lateral e clique em **Analisar cliente**.")


def tab_chat(customer: dict):
    st.subheader("Chat de retenção")
    st.caption("Pergunte sobre o cliente carregado na barra lateral.")
    if "chat" not in st.session_state:
        st.session_state["chat"] = []
    for role, content in st.session_state["chat"]:
        with st.chat_message(role):
            st.markdown(content)
    prompt = st.chat_input("Ex.: Qual a melhor oferta para reter esse cliente?")
    if prompt:
        st.session_state["chat"].append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"), st.spinner("Pensando..."):
            data = api_post("/chat", {"customer": customer, "message": prompt})
            answer = data["answer"] if data else "Falha ao consultar a API."
            st.markdown(answer)
        st.session_state["chat"].append(("assistant", answer))


def tab_monitor():
    st.subheader("Monitoramento")
    data = api_get("/metrics")
    if not data:
        st.info("Sem métricas ainda — faça algumas análises primeiro.")
        return
    s = data["summary"]
    cols = st.columns(5)
    cols[0].metric("Interações", s["n_interactions"])
    cols[1].metric("Latência média", f"{s['avg_latency_ms']} ms")
    cols[2].metric("Latência p95", f"{s['p95_latency_ms']} ms")
    cols[3].metric("Custo total", f"${s['total_cost_usd']:.4f}")
    cols[4].metric("Taxa fallback", f"{s['fallback_rate'] * 100:.0f}%")
    st.metric("Taxa de bloqueio por guardrail", f"{s['guardrail_block_rate'] * 100:.0f}%")
    st.markdown("#### Últimos traces")
    st.dataframe(data["recent"], use_container_width=True, height=300)


def main():
    st.title(":material/trending_down: ChurnPredictor")
    st.caption(
        "Recebe o perfil de um cliente, raciocina sobre o risco de churn (modelo ML + LLM) "
        "e recomenda uma ação de retenção. Trilha 1.1."
    )
    health = api_get("/health")
    if health:
        badge = (
            ":material/check_circle: online"
            if health.get("model_ready")
            else ":material/pending: modelo não treinado"
        )
        st.sidebar.caption(f"API: {badge}")
    else:
        st.sidebar.caption("API: :material/cancel: offline")

    customer = customer_form()
    t1, t2, t3 = st.tabs(
        [":material/analytics: Análise", ":material/chat: Chat de retenção", ":material/monitoring: Monitoramento"]
    )
    with t1:
        tab_analise(customer)
    with t2:
        tab_chat(customer)
    with t3:
        tab_monitor()


if __name__ == "__main__":
    main()
