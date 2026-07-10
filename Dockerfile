# Imagem única: API (FastAPI) + Produto (Streamlit) + nginx (reverse proxy).
# Mesma imagem roda local (docker compose) e no Hugging Face Spaces (porta 7860).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    API_BASE_URL=http://127.0.0.1:8000 \
    TRACE_LOG_PATH=/app/monitoring/traces.jsonl \
    HOME=/home/appuser

# nginx para o reverse proxy
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Treina o modelo no build (reprodutível: clone -> build -> sobe, sem passo manual).
RUN python -m ml.train

# Usuário não-root (uid 1000, exigência do HF Spaces) com HOME gravável.
RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app \
    && chmod +x start.sh
USER appuser

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:7860/api/health || exit 1

CMD ["bash", "start.sh"]
