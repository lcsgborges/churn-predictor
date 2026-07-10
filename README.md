---
title: ChurnPredictor
colorFrom: red
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# ChurnPredictor — Agente de Previsão de Churn

Sistema **agente → API → produto** que recebe o perfil de um cliente de telecom,
raciocina sobre o risco de cancelamento (churn) e devolve **probabilidade + explicação
+ ação de retenção**. Modelo de ML (Gradient Boosting + SHAP) para o número e os fatores;
LLM (OpenAI) para o raciocínio em linguagem natural; guardrails e fallback para confiabilidade.

- **Relatório completo:** [REPORT.md](REPORT.md)
- **Documentação (MkDocs):** pasta [`docs/`](docs/) · `mkdocs serve` · publicada no GitHub Pages
- **Deploy na VPS (EasyPanel):** [docs/deploy.md](docs/deploy.md)
- **Data card:** [data/DATA_CARD.md](data/DATA_CARD.md)

## Arquitetura (resumo)

```
Usuário → Streamlit (/) ─┐
                          ├─ nginx (:7860) ─┬─ /      → Streamlit (produto)
API externa → /api/* ─────┘                 └─ /api/* → FastAPI  → Agente (LLM + tools)
                                                                     └─ modelo ML + SHAP
```

Um único container serve **produto e API** no mesmo link.

## Rodar localmente (um comando)

```bash
cp .env.example .env      # opcional: preencha OPENAI_API_KEY (sem ela, roda em modo fallback)
docker compose up --build
```

- Produto: <http://localhost:7860/>
- API (docs): <http://localhost:7860/api/docs>
- Health: <http://localhost:7860/api/health>

Exemplo de chamada à API:

```bash
curl -X POST http://localhost:7860/api/predict -H 'Content-Type: application/json' -d '{
  "gender":"Female","SeniorCitizen":0,"Partner":"No","Dependents":"No","tenure":2,
  "PhoneService":"Yes","MultipleLines":"No","InternetService":"Fiber optic",
  "OnlineSecurity":"No","OnlineBackup":"No","DeviceProtection":"No","TechSupport":"No",
  "StreamingTV":"Yes","StreamingMovies":"Yes","Contract":"Month-to-month",
  "PaperlessBilling":"Yes","PaymentMethod":"Electronic check",
  "MonthlyCharges":95.0,"TotalCharges":190.0}'
```

## Desenvolvimento (sem Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m ml.train                                   # treina models/churn_model.pkl
uvicorn api.main:app --port 8000 &                   # API
streamlit run product/app.py                         # produto (usa API_BASE_URL=http://localhost:8000)
pytest                                               # testes
```

## Estrutura

| Pasta | Papel |
|---|---|
| `ml/` | pré-processamento, treino, predição e explicação (SHAP) |
| `agent/` | orquestração do agente, prompts, ferramentas, guardrails, fallback |
| `api/` | FastAPI (`/predict`, `/chat`, `/health`, `/metrics`) + schemas Pydantic |
| `product/` | painel Streamlit (Análise, Chat, Monitoramento) |
| `monitoring/` | tracing JSONL (latência, custo, fallback, guardrails) |
| `data/` | dataset Telco Churn + Data Card |

## Deploy no Hugging Face Spaces

O frontmatter no topo deste arquivo configura o Space (`sdk: docker`, `app_port: 7860`).
Crie um Space Docker, envie o repositório e defina `OPENAI_API_KEY` em *Settings → Secrets*.
