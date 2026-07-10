# Avaliação

## Performance do modelo

Teste estratificado (n = 1.409), taxa-base de churn ≈ 26,5%.

| Modelo | PR-AUC | ROC-AUC | Precisão | Recall (churn) | F1 | Limiar |
|---|---|---|---|---|---|---|
| Regressão Logística (baseline) | 0,633 | 0,842 | 0,524 | **0,765** | 0,622 | 0,54 |
| **Gradient Boosting (escolhido)** | **0,660** | 0,843 | 0,562 | 0,714 | **0,629** | 0,34 |

Se essas métricas forem novas para você, consulte as explicações de
[PR-AUC, ROC-AUC, F1, recall e limiar](glossario.md#metricas-de-aprendizado-de-maquina).

- **Critério:** maior **PR-AUC** (adequado ao desbalanceamento). O limiar **não** é 0,5 fixo — é tunado
  para maximizar F1.
- **Trade-off honesto:** o baseline tem recall maior; o GB tem melhor PR-AUC/precisão. Para retenção,
  um próximo passo é escolher o limiar por **custo de negócio** (custo da oferta × valor do cliente).
- **Reprodutível:** `python -m ml.train` regenera o modelo e o `models/metrics.json`.

## Avaliação do sistema

20 testes automatizados (`tests/`) cobrem:

- **Modelo:** probabilidade válida, alto risco > baixo risco, SHAP retorna fatores, `Contract` no topo.
- **Guardrails:** categoria inválida, numérico fora de faixa, jailbreak e fora de escopo bloqueados,
  saída incoerente sinalizada.
- **API:** health, `/predict` (200 + estrutura), schema inválido (422), chat com jailbreak bloqueado, `/metrics`.

```bash
pytest -q      # 20 passed
```

## Latência, custo e monitoramento

Cada interação vira um **trace** JSONL (`monitoring/tracing.py`), agregado em `/api/metrics` e na aba
**Monitoramento** do produto:

- **Latência** média e p95 (modo fallback ~0,2–0,3 s; com LLM, dominada pela chamada à OpenAI).
- **Custo** estimado por tokens (`gpt-4o-mini`).
- **Taxa de fallback** e **taxa de bloqueio por guardrail**.

## UX

- **Claro:** resposta padronizada *Risco → Por quê → Ação*, com medidor e gráfico de fatores.
- **Rápido:** perfis fictícios de exemplo (alto/baixo risco) para demonstração imediata.
- **Quando erra/tem incerteza:** a faixa de risco comunica confiança; no modo contingência, o sistema
  **avisa** que o LLM está indisponível mas que a previsão do modelo é válida.
