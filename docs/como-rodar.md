# Como rodar

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
python -m ml.train                        # treina models/churn_model.pkl
uvicorn api.main:app --port 8000 &        # API
streamlit run product/app.py              # produto
pytest -q                                 # 20 testes
```

## Rodar a documentação (MkDocs)

```bash
pip install -r requirements-docs.txt
mkdocs serve            # http://localhost:8000
mkdocs build            # gera site/ estático
```

## Deploy no Hugging Face Spaces

1. Crie um **Space** do tipo **Docker**.
2. Envie o conteúdo desta pasta (o `README.md` já traz o frontmatter `sdk: docker`, `app_port: 7860`).
3. Em **Settings → Secrets**, defina `OPENAI_API_KEY`.
4. O Space builda o `Dockerfile` e publica **produto + API** no mesmo link.

!!! tip "Deploy da documentação"
    O workflow `.github/workflows/docs.yml` (na raiz do repositório) publica esta documentação no
    **GitHub Pages** a cada push na `main`.
