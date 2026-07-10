#!/usr/bin/env bash
# Sobe os três processos no mesmo container e os supervisiona:
#   uvicorn (API, :8000) + streamlit (produto, :8501) + nginx (proxy público, :7860)
#
# Se QUALQUER um dos processos morrer (ex.: segfault do Streamlit), derrubamos os
# demais e saímos com status != 0. Assim o Docker/EasyPanel (política de restart)
# reinicia o container inteiro — em vez de ficar de pé com o nginx devolvendo 502
# por não ter mais upstream.
set -uo pipefail

pids=()

term() {
    for pid in "${pids[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
}
trap term SIGTERM SIGINT

echo "[start] subindo API (uvicorn :8000)..."
uvicorn api.main:app --host 127.0.0.1 --port 8000 --log-level info &
pids+=($!)

echo "[start] subindo produto (streamlit :8501)..."
streamlit run product/app.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --browser.gatherUsageStats false &
pids+=($!)

echo "[start] subindo nginx (proxy :7860)..."
nginx -c /app/nginx.conf -g 'daemon off;' &
pids+=($!)

# Bloqueia até QUALQUER processo terminar. Se um cair, encerra os outros e sai != 0
# para o container reiniciar (auto-recuperação).
wait -n
status=$?
echo "[start] um processo terminou (status $status) — encerrando o container para reiniciar."
term
exit 1
