"""Orquestrador do agente de retenção.

Fluxo por interação:
  1. Guardrails de ENTRADA (perfil do cliente + mensagem).
  2. Predição determinística (modelo ML) — base para raciocínio e para o fallback.
  3. Raciocínio do LLM via function calling (OpenAI). O LLM chama `predict_churn`;
     devolvemos o resultado já calculado (consistência e economia).
  4. Guardrail de SAÍDA (coerência/anti-alucinação).
  5. FALLBACK determinístico se o LLM falhar/estourar timeout ou a saída for incoerente.
  6. Trace de monitoramento (latência, tokens/custo, tools, fallback, guardrail).
"""
from __future__ import annotations

import json
import os
import time
import uuid

from agent.fallback import build_fallback_answer
from agent.guardrails import check_message, check_output, validate_customer
from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOLS, predict_churn
from monitoring.tracing import estimate_cost_usd, log_trace

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))


def _client():
    """Cria o client da OpenAI, ou None se não houver chave (força modo fallback)."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-xxxx"):
        return None
    from openai import OpenAI

    return OpenAI(api_key=api_key, timeout=LLM_TIMEOUT, max_retries=1)


def _build_user_content(customer: dict, message: str | None) -> str:
    profile = json.dumps(customer, ensure_ascii=False)
    base = f"Perfil do cliente (JSON):\n{profile}"
    if message:
        base += f"\n\nPergunta do time de retenção: {message}"
    else:
        base += "\n\nAvalie o risco de churn deste cliente e recomende uma ação."
    return base


def _run_llm(client, customer: dict, message: str | None, pre_result: dict) -> dict:
    """Loop de tool-calling. Retorna {answer, tools_used, tokens...}."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_content(customer, message)},
    ]
    tools_used: list[str] = []
    prompt_tokens = completion_tokens = 0

    for _ in range(3):  # no máx. 3 rodadas (evita loop de tool infinito)
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            tools=TOOLS,
            temperature=0.2,
        )
        usage = getattr(resp, "usage", None)
        if usage:
            prompt_tokens += usage.prompt_tokens or 0
            completion_tokens += usage.completion_tokens or 0

        msg = resp.choices[0].message
        if not msg.tool_calls:
            return {
                "answer": (msg.content or "").strip(),
                "tools_used": tools_used,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }

        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:
            tools_used.append(call.function.name)
            # Reusa a predição já calculada (fonte única, sem recomputar).
            result = pre_result if call.function.name == "predict_churn" else {}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    # Excedeu as rodadas sem resposta final.
    raise RuntimeError("LLM não produziu resposta final dentro do limite de rodadas.")


def analyze(customer: dict, message: str | None = None) -> dict:
    """Ponto de entrada do agente. Sempre retorna uma resposta utilizável."""
    trace_id = str(uuid.uuid4())[:8]
    t0 = time.perf_counter()
    meta = {
        "trace_id": trace_id,
        "fallback": False,
        "guardrail_blocked": False,
        "tools_used": [],
        "cost_usd": 0.0,
        "model": DEFAULT_MODEL,
    }

    # 1. Guardrails de entrada -------------------------------------------------
    g_customer = validate_customer(customer)
    if not g_customer.ok:
        return _finalize(
            answer=g_customer.message,
            prediction=None,
            meta={**meta, "guardrail_blocked": True, "guardrail_reason": g_customer.reason},
            details=g_customer.details,
            t0=t0,
        )
    g_msg = check_message(message)
    if not g_msg.ok:
        return _finalize(
            answer=g_msg.message,
            prediction=None,
            meta={**meta, "guardrail_blocked": True, "guardrail_reason": g_msg.reason},
            t0=t0,
        )

    # 2. Predição determinística (sempre disponível) ---------------------------
    pre_result = predict_churn(customer)

    # 3. Raciocínio do LLM (com fallback em caso de falha) ---------------------
    client = _client()
    if client is None:
        answer = build_fallback_answer(pre_result)
        meta["fallback"] = True
        meta["fallback_reason"] = "no_api_key"
        return _finalize(answer, pre_result, meta, t0=t0)

    try:
        llm = _run_llm(client, customer, message, pre_result)
        meta["tools_used"] = llm["tools_used"]
        meta["cost_usd"] = estimate_cost_usd(
            llm["prompt_tokens"], llm["completion_tokens"]
        )
        meta["prompt_tokens"] = llm["prompt_tokens"]
        meta["completion_tokens"] = llm["completion_tokens"]

        # 4. Guardrail de saída ------------------------------------------------
        g_out = check_output(llm["answer"], pre_result)
        if not g_out.ok:
            meta["fallback"] = True
            meta["fallback_reason"] = f"output_guardrail:{g_out.reason}"
            answer = build_fallback_answer(pre_result)
        else:
            answer = llm["answer"]
        return _finalize(answer, pre_result, meta, t0=t0)

    except Exception as exc:  # timeout, erro de API, etc. -> degrada
        meta["fallback"] = True
        meta["fallback_reason"] = f"llm_error:{type(exc).__name__}"
        answer = build_fallback_answer(pre_result)
        return _finalize(answer, pre_result, meta, t0=t0)


def _finalize(answer, prediction, meta, t0, details=None) -> dict:
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    result = {
        "answer": answer,
        "prediction": prediction,
        "meta": {**meta, "latency_ms": latency_ms},
    }
    if details:
        result["details"] = details
    log_trace(
        {
            "trace_id": meta.get("trace_id"),
            "latency_ms": latency_ms,
            "cost_usd": meta.get("cost_usd", 0.0),
            "fallback": meta.get("fallback", False),
            "fallback_reason": meta.get("fallback_reason"),
            "guardrail_blocked": meta.get("guardrail_blocked", False),
            "guardrail_reason": meta.get("guardrail_reason"),
            "tools_used": meta.get("tools_used", []),
            "model": meta.get("model"),
            "churn_pct": prediction.get("churn_probability_pct") if prediction else None,
        }
    )
    return result
