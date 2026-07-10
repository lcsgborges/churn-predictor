# Problema

## A dor

Em telecom, o **churn** (cancelamento) é um dos maiores vazamentos de receita — reter custa muito
menos do que adquirir. O time de retenção não consegue ligar para todos: precisa saber **quem** está
em risco e **por quê**, para escolher a oferta certa. Uma probabilidade solta não aciona ninguém; o
valor está em transformar a previsão em **ação priorizada e justificada**.

## Stakeholders

| Stakeholder | Papel |
|---|---|
| Time de retenção / call center | Usuário direto: recebe risco + explicação + ação |
| Gestão de CRM / receita | Acompanha volume de risco e efetividade das ações |
| Cliente final | Afetado: recebe (ou não) uma oferta — exige cuidado com viés (ver [Ética](etica.md)) |

## Métricas de sucesso

=== "Negócio"
    Taxa de retenção dos clientes de alto risco contatados e redução do churn evitável.
    Operacionalmente: o analista decide a ação em segundos, com justificativa.

=== "Técnica"
    Classe desbalanceada (~26,5% de churn) → métrica primária **PR-AUC (Average Precision)** +
    **Recall da classe churn**. Acurácia isolada é enganosa e foi descartada.

## Por que ML (e não uma regra simples)

Regras do tipo "contrato mensal = risco" capturam parte do sinal, mas o churn depende de **interações**
entre tempo de casa, tipo de serviço, forma de pagamento e valor — que o Gradient Boosting modela e o
SHAP explica cliente a cliente.
