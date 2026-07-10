# Como rodar

## Pré-requisitos

- **Docker + Docker Compose** para o caminho recomendado; ou
- **Python 3.12** para executar sem Docker.

A chave `OPENAI_API_KEY` é opcional. Sem ela, a aplicação continua fazendo previsões e usa o
fallback determinístico para explicar o resultado.

## Com Docker (recomendado — um comando)

```bash
cp .env.example .env      # opcional: preencha OPENAI_API_KEY (sem ela, roda em modo fallback)
docker compose up --build
```

- Produto: <http://localhost:7860/>
- API (docs): <http://localhost:7860/api/docs>
- Health: <http://localhost:7860/api/health>

## Chamando a API

```bash
curl -X POST http://localhost:7860/api/predict -H 'Content-Type: application/json' -d '{
  "gender":"Female","SeniorCitizen":0,"Partner":"No","Dependents":"No","tenure":2,
  "PhoneService":"Yes","MultipleLines":"No","InternetService":"Fiber optic",
  "OnlineSecurity":"No","OnlineBackup":"No","DeviceProtection":"No","TechSupport":"No",
  "StreamingTV":"Yes","StreamingMovies":"Yes","Contract":"Month-to-month",
  "PaperlessBilling":"Yes","PaymentMethod":"Electronic check",
  "MonthlyCharges":95.0,"TotalCharges":190.0}'
```

Resposta (resumo):

```json
{
  "answer": "**Risco:** ALTO — probabilidade **77.7%** ...",
  "churn_probability_pct": 77.7,
  "risk_band": "alto",
  "factors": [{"feature": "Contract", "direction": "aumenta", ...}],
  "meta": {"latency_ms": 244.2, "fallback": true, "trace_id": "..."}
}
```

## Sem Docker (desenvolvimento)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m ml.train                                  # treina models/churn_model.pkl
uvicorn api.main:app --reload --port 7860           # UI (/) + API (/api/*) no mesmo processo
pytest -q                                           # testes
```

Abra <http://localhost:7860/> para o produto e <http://localhost:7860/api/docs> para a API.

## Rodar a documentação (MkDocs)

```bash
pip install -r requirements-docs.txt
mkdocs serve            # http://localhost:8000
mkdocs build            # gera site/ estático
```

## Deploy em produção (VPS + EasyPanel)

O sistema roda numa VPS via **EasyPanel**: um único container, build a partir do `Dockerfile`
(Build Path `/`) e `OPENAI_API_KEY` nas variáveis de ambiente. O passo a passo
completo está em [Deploy na VPS (EasyPanel)](deploy.md). App no ar: <https://churn.lcsgborges.cloud/>.

!!! tip "Deploy da documentação"
    O workflow `.github/workflows/docs.yml` (na raiz do repositório) publica esta documentação no
    **GitHub Pages** a cada push na `main`.
