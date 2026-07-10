# Impactos e ética

Pensando **neste** problema (retenção em telecom), não em ética genérica.

## Quem pode ser prejudicado por um erro

- **Falso negativo:** deixa escapar um cliente que iria cancelar → perda de receita.
- **Falso positivo:** gasta oferta com quem ficaria de qualquer forma → custo e possível desigualdade
  se as ofertas se concentrarem em certos grupos.

## Viés entre grupos

O dataset contém `gender` e `SeniorCitizen`, e `MonthlyCharges`/`Contract` podem ser **proxies de renda**.
Há risco de a política de retenção favorecer sistematicamente um grupo.

!!! warning "Mitigação recomendada"
    - Auditar **taxa de acerto** e **taxa de oferta** por grupo (gênero, faixa etária, ticket).
    - Considerar remover atributos sensíveis do modelo se não agregarem valor preditivo justo.
    - Definir o limiar por custo de negócio de forma **uniforme** entre grupos.

## Privacidade e segurança

- Perfis de clientes são **dados pessoais**. O sistema **não persiste PII** nos traces — guarda apenas
  métricas e a probabilidade.
- A chave da OpenAI fica em **variável de ambiente / secret**, nunca no código.
- **Guardrails** barram injeção de prompt e uso fora de escopo.
- Em produção, recomenda-se **autenticação** na API e **retenção mínima** de dados.

## Limitações do dado

Dataset sintético/EUA (IBM Sample Data): padrões podem **não generalizar** para o mercado brasileiro.
Ver o [Data Card](https://github.com/lcsgborges/churn-predictor/blob/main/data/DATA_CARD.md) no
repositório (`data/DATA_CARD.md`).
