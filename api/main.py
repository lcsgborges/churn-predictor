"""API FastAPI que expõe o agente de churn.

Rotas (servidas atrás do nginx em `/api`):
  GET  /health           -> status do serviço e do modelo
  POST /predict          -> perfil do cliente => risco + explicação + ação
  POST /chat             -> perfil + pergunta livre => resposta conversacional
  GET  /metrics          -> resumo de monitoramento (latência, custo, fallback...)
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from agent.agent import analyze
from api.schemas import AgentResponse, ChatRequest, CustomerProfile
from ml.model import ModelNotTrainedError, load_bundle
from monitoring.tracing import read_traces, summarize


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aquece o modelo no boot (falha cedo e explícito se não estiver treinado).
    try:
        load_bundle()
        app.state.model_ready = True
    except ModelNotTrainedError:
        app.state.model_ready = False
    yield


app = FastAPI(
    title="Agente de Previsão de Churn",
    description="Trilha 1.1 — recebe o perfil de um cliente, raciocina sobre o risco de "
    "churn e devolve probabilidade, explicação e ação de retenção.",
    version="1.0.0",
    lifespan=lifespan,
)


def _to_response(result: dict) -> AgentResponse:
    pred = result.get("prediction") or {}
    return AgentResponse(
        answer=result["answer"],
        churn_probability=pred.get("churn_probability"),
        churn_probability_pct=pred.get("churn_probability_pct"),
        risk_band=pred.get("risk_band"),
        will_churn=pred.get("will_churn"),
        factors=pred.get("factors", []),
        meta=result["meta"],
    )


@app.get("/health")
def health():
    ready = getattr(app.state, "model_ready", False)
    return {"status": "ok" if ready else "degraded", "model_ready": ready}


@app.post("/predict", response_model=AgentResponse)
def predict(customer: CustomerProfile):
    result = analyze(customer.model_dump())
    return _to_response(result)


@app.post("/chat", response_model=AgentResponse)
def chat(req: ChatRequest):
    result = analyze(req.customer.model_dump(), message=req.message)
    return _to_response(result)


@app.get("/metrics")
def metrics(limit: int = 500):
    traces = read_traces(limit=limit)
    return {"summary": summarize(traces), "recent": traces[-50:]}


@app.exception_handler(Exception)
async def unhandled(_request, exc):
    # Nunca vaza stacktrace cru ao usuário final.
    return JSONResponse(
        status_code=500,
        content={
            "answer": "Desculpe, tivemos um problema técnico ao processar sua solicitação. "
            "Tente novamente em instantes.",
            "meta": {"error": type(exc).__name__},
        },
    )
