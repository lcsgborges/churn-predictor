# Data Card — Telco Customer Churn

## Origem
- **Dataset:** Telco Customer Churn (amostra de dados de exemplo da IBM).
- **Fonte usada no projeto:** mirror oficial da IBM no GitHub
  (`IBM/telco-customer-churn-on-icp4d`, arquivo `data/Telco-Customer-Churn.csv`).
- **Fonte original / referência Kaggle:** <https://www.kaggle.com/datasets/blastchar/telco-customer-churn>
- **Volume:** 7.043 clientes, 21 colunas.
- **Alvo:** coluna `Churn` (`Yes`/`No`) — o cliente cancelou o serviço no último mês.

## Licença
- Distribuído pela IBM como **IBM Sample Data**, para fins de aprendizado e demonstração.
  Uso **educacional/acadêmico** — este projeto é um trabalho de disciplina, sem fim comercial.
- O mirror da IBM no GitHub redistribui o CSV publicamente para tutoriais.

## Dicionário de dados (resumo)
| Grupo | Colunas |
|---|---|
| Identificador (descartado no treino) | `customerID` |
| Demografia | `gender`, `SeniorCitizen`, `Partner`, `Dependents` |
| Conta | `tenure`, `Contract`, `PaperlessBilling`, `PaymentMethod`, `MonthlyCharges`, `TotalCharges` |
| Serviços | `PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies` |
| Alvo | `Churn` |

## Preparação (ver `ml/preprocess.py`)
- `TotalCharges` vem como texto e tem ~11 células em branco (clientes com `tenure=0`,
  recém-chegados). Convertidas para número e preenchidas com `0.0`.
- Numéricas escalonadas (`StandardScaler`); categóricas em `OneHotEncoder(handle_unknown="ignore")`.
- Split estratificado 80/20 pela variável alvo.

## Desbalanceamento
- Taxa base de churn ≈ **26,5%** (classe positiva minoritária). Por isso a métrica principal é
  **PR-AUC** (Average Precision) + **Recall** da classe churn, e não acurácia. O baseline usa
  `class_weight="balanced"`; o limiar de decisão é tunado (não fixado em 0,5).

## Vieses conhecidos e cuidados
- **Representatividade:** dados sintéticos/de exemplo de uma operadora fictícia dos EUA. Padrões
  podem **não** generalizar para o mercado brasileiro ou outras operadoras.
- **Atributos sensíveis:** contém `gender` e `SeniorCitizen`. Uma ação de retenção guiada pelo modelo
  não deve discriminar por esses grupos — ver a seção *Impactos e Ética* no relatório.
- **Proxy de renda:** `MonthlyCharges`/`Contract` podem correlacionar com capacidade de pagamento;
  atenção para não penalizar sistematicamente clientes de menor ticket.
- **Sem dado temporal explícito de causa:** o dataset é um snapshot; não há série temporal do
  comportamento que levou ao churn.

## Uso no sistema
- Treina o modelo (`ml/train.py`) e serve de **contexto de inferência**: a API recebe um perfil
  novo de cliente (mesmo esquema de colunas) e o agente raciocina sobre ele em tempo real.
