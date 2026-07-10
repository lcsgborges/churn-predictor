# Reflexão sobre o que aprendemos

## O que funcionou bem

- **Separar responsabilidades:** o modelo decide o número, o LLM comunica. Isso deu **confiabilidade**
  (fallback trivial) e **auditabilidade** (explicação ancorada em SHAP, à prova de alucinação).
- **Uma ferramenta forte** em vez de várias fracas: menos latência, menos chamadas ao LLM e menos
  superfície de erro.

## O que não funcionou como planejado

- O **prompt v1** deixava o LLM "chutar" a probabilidade e dar conselhos genéricos. Resolvido com regra
  dura (número só da ferramenta) **+ guardrail de saída** que descarta respostas incoerentes.
- A escolha do **limiar por F1** é subótima para o negócio — o ideal é decidir por custo (oferta × valor
  do cliente).

## Limitações do dado

- Dataset sintético/EUA (IBM Sample Data): os padrões podem **não generalizar** para o mercado brasileiro.

## Próximos passos

- Limiar por **custo de negócio** em vez de F1.
- **Teste A/B** das ofertas de retenção.
- **Cache** de respostas e **autenticação** na API.
- **Persistir os traces** em banco (hoje é JSONL efêmero no container).
