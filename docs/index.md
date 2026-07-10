# Agente de Previsão de Churn

> **Trilha 1 · Projeto 1.1** — classificação tabular com raciocínio, API e produto no ar.

Sistema **agente → API → produto** que recebe o perfil de um cliente de telecom, **raciocina**
sobre o risco de cancelamento (churn) e devolve **probabilidade + explicação + ação de retenção**.

<div class="grid cards" markdown>

- :material-brain: **Agente, não só modelo**
  O modelo de ML dá o número e os fatores; o LLM traduz em explicação e recomenda a ação.

- :material-shield-check: **Confiável**
  Guardrails de entrada/saída e *fallback* determinístico quando o LLM falha.

- :material-docker: **Deployable**
  Um `docker compose up` sobe produto **e** API no mesmo link.

- :material-chart-line: **Observável**
  Traces de latência, custo, fallback e guardrails.

</div>

## Links

- **Aplicação:** _preencher após deploy_ (`https://<seu-space>.hf.space/`)
- **API:** `/api/docs` · `/api/predict` · `/api/health`
- **Repositório:** _preencher_
- **Relatório completo:** [`REPORT.md`](https://github.com/) _(no repositório)_

## O que ele faz, em uma frase

Dado um cliente de alto risco (contrato mensal, pouco tempo de casa, fibra sem suporte), o sistema
responde algo como:

!!! quote "Resposta do agente"
    **Risco:** ALTO — probabilidade **77,7%** (taxa-base da carteira: 26,5%).
    **Por quê:** contrato mensal, cliente novo (2 meses), cobrança mensal alta.
    **Ação recomendada:** oferecer migração para contrato anual com desconto; acionar o time de relacionamento.

Continue por [Problema](problema.md) → [Arquitetura](arquitetura.md) → [Como rodar](como-rodar.md).
