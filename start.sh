#!/usr/bin/env bash
# Sobe os três processos no mesmo container:
#   uvicorn (API, :8000) + streamlit (produto, :8501) + nginx (proxy público, :7860)
set -euo pipefail

echo "[start] subindo API (uvicorn :8000)..."
uvicorn api.main:app --host 127.0.0.1 --port 8000 --log-level info &

echo "[start] subindo produto (streamlit :8501)..."
streamlit run product/app.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --browser.gatherUsageStats false &

echo "[start] subindo nginx (proxy :7860)..."
exec nginx -c /app/nginx.conf -g 'daemon off;'
