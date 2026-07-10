# Imagem única: API (FastAPI) + Produto (Streamlit) + nginx (reverse proxy).
# Mesma imagem roda local (docker compose) e no Hugging Face Spaces (porta 7860).
# Build multi-stage: o builder instala dependências e treina o modelo; o runtime
# recebe só o venv pronto + o app + o modelo, ficando mais enxuto e rápido de subir.

# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# venv isolado — fácil de copiar inteiro para o estágio final.
RUN python -m venv /opt/venv

# Camada de dependências em separado: só reinstala quando requirements.txt muda.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Treina o modelo no build (reprodutível: clone -> build -> sobe, sem passo manual).
COPY . .
RUN python -m ml.train

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    API_BASE_URL=http://127.0.0.1:8000 \
    TRACE_LOG_PATH=/app/monitoring/traces.jsonl \
    HOME=/home/appuser \
    # Evita oversubscription de threads nativas (numpy/OpenBLAS/OMP), causa comum de
    # segfault e consumo de memória em containers com CPU/memória restritas.
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1

# Só o necessário em runtime: nginx (reverse proxy) + curl (healthcheck).
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# venv já com as dependências e o app já com o modelo treinado (do builder).
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

# Usuário não-root (uid 1000, exigência do HF Spaces) com HOME gravável.
RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app \
    && chmod +x start.sh
USER appuser

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:7860/api/health || exit 1

CMD ["bash", "start.sh"]
