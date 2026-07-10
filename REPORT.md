# Relatório — Agente de Previsão de Churn

> **Trilha 1 · Projeto 1.1 — Previsão de churn (classificação tabular)**

| | |
|---|---|
| **Aplicação (link):** | https://churn.lcsgborges.cloud/ |
| **API (link):** | https://churn.lcsgborges.cloud/api/docs · `/api/predict` · `/api/health` |
| **Documentação:** | https://lcsgborges.github.io/churn-predictor/ |
| **Repositório:** | https://github.com/lcsgborges/churn-predictor |
| **Vídeo demo:** | _preencher_ |
| **Integrantes:** | Lucas Guimarães |

---

## 1. Definição do problema

**Que dor é essa e por que importa.** Em telecom, cancelamento (churn) é um dos maiores vazamentos
de receita: adquirir um novo cliente custa muito mais do que reter um existente. O time de retenção,
porém, não consegue ligar para todo mundo — precisa saber **quem** está em risco e, principalmente,
**por quê**, para escolher a oferta certa. Um número de probabilidade sozinho não aciona ninguém; o
valor está em transformar a previsão em uma **ação priorizada e justificada**.

**Stakeholders.**
- **Time de retenção / call center** (usuário direto): recebe o risco e a ação sugerida.
- **Gestão de CRM / receita**: acompanha volume de risco e efetividade das ações.
- **Cliente final** (afetado): recebe (ou não) uma oferta de retenção — daí a importância de não
  discriminar grupos (ver §7).

**Métrica de sucesso.**
- **De negócio:** taxa de retenção dos clientes de alto risco contatados (quantos, entre os sinalizados,
  foram convencidos a ficar) e redução do churn evitável. Proxy operacional: o analista consegue decidir a
  ação em segundos, com justificativa.
- **Técnica:** como a classe é desbalanceada (~26,5% de churn), a métrica primária é **PR-AUC
  (Average Precision)** somada ao **Recall da classe churn** (não perder quem vai cancelar). Acurácia
  isolada é enganosa e foi descartada.

---

## 2. Como o sistema é montado

### Diagrama de arquitetura

```
                        Link público único — nginx (porta 7860)
                 ┌───────────────────────────────────────────────┐
   Navegador ───▶│  /        → Streamlit  (produto :8501)         │
   Sistemas  ───▶│  /api/*   → FastAPI    (API :8000)             │
                 └───────────────────┬───────────────────────────┘
                                     ▼
                       ┌─────────────────────────────┐
                       │  Agente (agent/agent.py)     │
                       │  1. Guardrails de ENTRADA    │  perfil + mensagem
                       │  2. predict_churn (tool) ────┼──▶ Pipeline sklearn (.pkl)
                       │        └─ SHAP (fatores)     │      Gradient Boosting
                       │  3. Raciocínio LLM (OpenAI)  │
                       │  4. Guardrails de SAÍDA      │
                       │  5. FALLBACK determinístico  │
                       └───────────────┬─────────────┘
                                       ▼
                Resposta: probabilidade + explicação + ação de retenção
                                       ▼
                Monitoring (JSONL): latência · custo · fallback · guardrails
```

### Agent/model exploration (o que consideramos)

- **Tipo de agente.** Consideramos (a) um classificador "puro" exposto via API e (b) um agente com
  raciocínio. Escolhemos o **agente com function calling**: o modelo ML entrega o número e os fatores;
  o LLM os traduz em explicação e ação. Isso materializa a diferença "modelo → agente" pedida no enunciado.
- **Ferramentas.** Optamos por **uma ferramenta única e forte** (`predict_churn`, que embrulha modelo + SHAP)
  em vez de várias ferramentas fracas — menos latência, menos superfície de erro. O LLM é **proibido** de
  inventar a probabilidade; ela vem só da ferramenta.
- **Modelo base do agente.** `gpt-4o-mini` — barato, baixa latência e suficiente para raciocínio estruturado
  sobre poucos fatores. Alternativas maiores não se justificavam pelo custo/latência para este escopo.
- **Modelo preditivo.** Comparamos **Regressão Logística** (baseline) e **Gradient Boosting** (ver §4).

### Deployment

- **Empacotamento:** um único **Dockerfile** instala tudo, **treina o modelo no build** (reprodutível:
  clone → `docker compose up` → sistema no ar) e roda **três processos** via `start.sh`: uvicorn (API),
  Streamlit (produto) e **nginx** como reverse proxy.
- **Exposição:** o HF Spaces publica **uma** porta. O nginx roteia `/` → produto e `/api/*` → API, então
  **produto e API ficam no mesmo link público** (`/api/predict`, `/api/health`, `/api/docs`).
- **Entradas em produção:** a API recebe perfis novos de clientes (mesmo esquema do dataset) via `POST /api/predict`
  ou `POST /api/chat`; o produto Streamlit monta esse JSON a partir do formulário.

### CI/CD e estratégia de confiabilidade

- **CI (GitHub Actions, `.github/workflows/ci.yml`):** lint (ruff) → treino do modelo → testes (pytest) →
  build da imagem Docker. Quebra o merge se algo falhar.
- **Confiabilidade (o que acontece quando algo cai):**
  - LLM fora do ar / sem chave / timeout → **fallback determinístico** monta a resposta só com o modelo ML
    (nunca erro cru; o usuário é avisado do modo contingência).
  - Erro inesperado na API → handler global devolve mensagem amigável, sem stacktrace.
  - Categoria desconhecida no pré-processador → `handle_unknown="ignore"` evita quebra.

---

## 3. Descrição do agente

### Modelo base e ferramentas
- **LLM:** `gpt-4o-mini` (OpenAI), `temperature=0.2`, `timeout=20s`, 1 retry. Escolha por **custo e latência**.
- **Ferramenta `predict_churn`:** recebe o perfil, roda o pipeline sklearn e o SHAP, e devolve
  probabilidade, faixa de risco, limiar, taxa-base e os **fatores** (com direção "aumenta/reduz").
  É a **única** fonte da probabilidade e das causas.

### Dados e contexto
- **Telco Customer Churn** (IBM Sample Data), 7.043 clientes, 21 colunas, alvo `Churn`. Origem, licença e
  vieses no [Data Card](data/DATA_CARD.md). Preparo em `ml/preprocess.py` (limpeza de `TotalCharges`,
  one-hot + escala). O dado **treina o modelo** e define o **esquema de inferência** que a API aceita.

### Guardrails
- **Entrada:**
  - *Schema (Pydantic):* valores categóricos restritos e faixas numéricas — entrada inválida vira **HTTP 422**
    antes de chegar ao agente.
  - *Perfil (`validate_customer`):* revalida categorias/faixas na camada do agente.
  - *Mensagem (`check_message`):* bloqueia **jailbreak / prompt injection** e pedidos **fora de escopo**.
- **Saída (`check_output`):**
  - Rejeita resposta vazia.
  - *Anti-alucinação de número:* se a porcentagem citada pelo LLM diverge >8pp da probabilidade real do
    modelo, a resposta é descartada e cai no fallback.
- **O que acontece quando dispara:** entrada bloqueada → mensagem educada de reorientação (sem gastar LLM);
  saída incoerente → resposta de fallback determinística. Tudo é registrado no trace.

### Iterações de prompt e design (incl. o que NÃO funcionou)
- **v1 (baseline):** prompt genérico ("diga a probabilidade e sugira algo"). **Falhou** em dois pontos:
  o LLM às vezes **inventava** uma probabilidade diferente do modelo e dava conselhos genéricos sem citar
  as causas reais.
- **v_final:** regras inegociáveis — (1) probabilidade **só** da ferramenta; (2) explicação **ancorada**
  nos `factors`; (3) formato fixo *Risco → Por quê → Ação*; (4) escopo travado. O guardrail de saída foi
  adicionado justamente para capturar a falha da v1 em runtime.
- **Ferramentas:** começamos cogitando várias tools (uma para prob, outra para explicação, outra para
  ofertas). **Descartado:** aumentava latência e chamadas ao LLM sem ganho — consolidamos em `predict_churn`.
- **Explicação:** SHAP por instância (TreeExplainer) com **degradação** para importância global caso o SHAP
  falhe — a resposta nunca quebra por causa da explicação.

---

## 4. Avaliação do sistema

### Performance do modelo (teste estratificado, n=1.409)

| Modelo | PR-AUC | ROC-AUC | Precisão | Recall (churn) | F1 | Limiar |
|---|---|---|---|---|---|---|
| Regressão Logística (baseline) | 0,633 | 0,842 | 0,524 | **0,765** | 0,622 | 0,54 |
| **Gradient Boosting (escolhido)** | **0,660** | 0,843 | 0,562 | 0,714 | **0,629** | 0,34 |

- **Critério de escolha:** maior **PR-AUC** (adequado ao desbalanceamento). O limiar não foi fixado em 0,5:
  é **tunado** para maximizar F1 (equilíbrio precisão/recall).
- **Trade-off honesto:** o baseline tem recall maior; o GB tem melhor PR-AUC e precisão. Para retenção,
  um recall alto importa (não perder quem vai sair) — um próximo passo é escolher o limiar por **custo de
  negócio** (custo de uma oferta vs. valor do cliente), não só por F1.
- **Reprodutível:** `python -m ml.train` regenera o modelo e o `models/metrics.json` com as duas abordagens.

### Avaliação do agente / sistema
- **Casos extremos testados** (`tests/`, 20 testes): entrada inválida (422), categoria inexistente,
  numérico fora de faixa, **jailbreak** e **fora de escopo** bloqueados, saída incoerente → fallback,
  fallback sem chave de LLM.
- **Latência:** modo fallback ~0,2–0,3 s; com LLM, dominada pela chamada à OpenAI (medida por trace).
- **Custo:** estimado por tokens em cada trace (aba Monitoramento e `/api/metrics`).
- **Taxa de fallback e de guardrail:** agregadas no monitoramento.

### UX
- **Claro:** resposta padronizada *Risco → Por quê → Ação*, com medidor visual e gráfico de fatores.
- **Rápido:** presets de cliente (alto/baixo risco) para demonstração imediata.
- **Quando erra/tem incerteza:** faixa de risco (alto/médio/baixo) comunica confiança; no modo contingência,
  o sistema **avisa** que o LLM está indisponível mas que a previsão do modelo é válida.

---

## 5. Demonstração

_Vídeo: preencher o link._ Roteiro sugerido: (1) carregar preset "Alto risco" → analisar → mostrar
probabilidade, fatores SHAP e ação; (2) usar o chat de retenção; (3) tentar um jailbreak → guardrail;
(4) chamar a API pública via `curl /api/predict`; (5) abrir a aba Monitoramento.

---

## 6. Reflexão sobre o que aprenderam

- **Funcionou bem:** separar responsabilidades — o modelo decide o número, o LLM comunica. Isso deu
  **confiabilidade** (fallback trivial) e **auditabilidade** (explicação ancorada em SHAP).
- **Não funcionou como planejado:** o prompt v1 deixava o LLM "chutar" probabilidade; resolvido com regra
  dura + guardrail de saída. A escolha do limiar por F1 é subótima para o negócio.
- **Limitações do dado:** dataset sintético/EUA; padrões podem não generalizar para o Brasil.
- **Próximos passos:** limiar por custo de negócio; teste A/B das ofertas; cache de respostas; autenticação
  na API; persistência dos traces em banco (hoje é JSONL efêmero no container).

---

## 7. Impactos e ética

- **Quem pode ser prejudicado por um erro:** um **falso negativo** deixa escapar um cliente que iria cancelar
  (perda de receita); um **falso positivo** gasta oferta com quem ficaria de qualquer forma (custo, e possível
  desigualdade se as ofertas se concentrarem em certos grupos).
- **Viés entre grupos:** o dataset contém `gender` e `SeniorCitizen`, e `MonthlyCharges`/`Contract` podem
  ser **proxies de renda**. Risco de a política de retenção favorecer sistematicamente um grupo. **Mitigação
  recomendada:** auditar as taxas de acerto e de oferta por grupo (fairness), e considerar remover atributos
  sensíveis do modelo se não agregarem valor preditivo justo.
- **Privacidade/segurança:** perfis de clientes são dados pessoais. No sistema, não persistimos PII nos
  traces (guardamos só métricas e a probabilidade); a chave da OpenAI fica em variável de ambiente/secret;
  guardrails barram injeção de prompt. Em produção, recomenda-se autenticação e retenção mínima de dados.

---

## 8. Referências

- **Dataset:** Telco Customer Churn — IBM Sample Data ·
  Kaggle: <https://www.kaggle.com/datasets/blastchar/telco-customer-churn> ·
  Mirror IBM: <https://github.com/IBM/telco-customer-churn-on-icp4d>
- **Bibliotecas:** scikit-learn, SHAP, FastAPI, Streamlit, OpenAI Python SDK, Plotly, nginx, Docker.
- **Modelo LLM:** OpenAI `gpt-4o-mini`.
- **Explicabilidade:** Lundberg & Lee, *A Unified Approach to Interpreting Model Predictions* (SHAP), 2017.
