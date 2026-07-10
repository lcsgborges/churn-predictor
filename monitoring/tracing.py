"""Monitoramento: registro de traces em JSONL e agregação de métricas.

Cada interação com o agente vira uma linha JSON com: entrada (resumida), ferramentas
acionadas, latência ponta-a-ponta, tokens/custo do LLM, se o fallback foi acionado e se
algum guardrail bloqueou. A aba de Monitoramento do produto lê este arquivo.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

TRACE_LOG_PATH = os.getenv("TRACE_LOG_PATH", "monitoring/traces.jsonl")

# Preço aproximado do gpt-4o-mini (USD por 1M tokens) — usado só para estimar custo.
_PRICE_PER_1M = {"input": 0.15, "output": 0.60}
_LOCK = threading.Lock()


def estimate_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    """Estima o custo em USD de uma chamada ao LLM a partir da contagem de tokens."""
    return round(
        prompt_tokens / 1_000_000 * _PRICE_PER_1M["input"]
        + completion_tokens / 1_000_000 * _PRICE_PER_1M["output"],
        6,
    )


def log_trace(trace: dict) -> None:
    """Anexa um trace ao arquivo JSONL (thread-safe, best-effort)."""
    record = {"ts": datetime.now(timezone.utc).isoformat(), **trace}
    try:
        path = Path(TRACE_LOG_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK, path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # Monitoramento nunca deve derrubar a requisição do usuário.
        pass


def read_traces(limit: int = 500) -> list[dict]:
    """Lê os últimos `limit` traces do arquivo (mais recentes por último)."""
    path = Path(TRACE_LOG_PATH)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def summarize(traces: list[dict]) -> dict:
    """Agrega métricas para o painel: latência, custo, fallback e guardrails."""
    n = len(traces)
    if n == 0:
        return {
            "n_interactions": 0,
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "total_cost_usd": 0.0,
            "fallback_rate": 0.0,
            "guardrail_block_rate": 0.0,
        }
    latencies = sorted(t.get("latency_ms", 0) for t in traces)
    p95_idx = min(n - 1, int(round(0.95 * (n - 1))))
    return {
        "n_interactions": n,
        "avg_latency_ms": round(sum(latencies) / n, 1),
        "p95_latency_ms": round(latencies[p95_idx], 1),
        "total_cost_usd": round(sum(t.get("cost_usd", 0.0) for t in traces), 6),
        "fallback_rate": round(sum(1 for t in traces if t.get("fallback")) / n, 3),
        "guardrail_block_rate": round(
            sum(1 for t in traces if t.get("guardrail_blocked")) / n, 3
        ),
    }
