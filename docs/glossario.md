# Glossário

Este glossário explica, em linguagem simples, as siglas e os termos técnicos usados no projeto.

## Como ler o log de treinamento

Durante o build da imagem Docker, podem aparecer linhas como estas:

```text
#11 [builder 7/7] RUN python -m ml.train
#11 3.462 [logistic_regression] PR-AUC=0.633 ROC-AUC=0.842 F1=0.622 recall=0.765 thr=0.54
#11 5.052 [gradient_boosting] PR-AUC=0.660 ROC-AUC=0.843 F1=0.629 recall=0.714 thr=0.34
#11 5.052 >> Modelo escolhido: gradient_boosting (maior PR-AUC)
```

Isso **não é um erro**. É o Docker mostrando o progresso do build e o programa comparando dois
modelos de previsão.

| Trecho | Significado |
|---|---|
| `#11` | Identificador da etapa atual do build do Docker. |
| `[builder 7/7]` | Sétima e última instrução do estágio chamado `builder` no Dockerfile. |
| `RUN python -m ml.train` | Executa o módulo `ml.train`, responsável por treinar e avaliar os modelos. |
| `3.462` / `5.052` | Tempo aproximado, em segundos, desde o início dessa etapa. |
| `[logistic_regression]` | Resultados da Regressão Logística, usada como modelo de referência (*baseline*). |
| `[gradient_boosting]` | Resultados do Gradient Boosting, modelo mais flexível avaliado pelo projeto. |
| `PR-AUC=0.660` | Qualidade do modelo ao identificar churn, considerando diferentes limiares. Quanto maior, melhor. |
| `ROC-AUC=0.843` | Capacidade de ordenar clientes com e sem churn. Quanto mais próximo de 1, melhor. |
| `F1=0.629` | Equilíbrio entre precisão e recall. Quanto maior, melhor. |
| `recall=0.714` | O modelo encontrou cerca de 71,4% dos clientes que realmente cancelaram. |
| `thr=0.34` | Limiar escolhido: probabilidade a partir de 34% é classificada como churn. |
| `Modelo escolhido` | Informa qual modelo foi salvo para uso pela aplicação e qual foi o critério da escolha. |

Os valores usam ponto como separador decimal. Portanto, `0.660` equivale a `0,660` e não significa
66% de acerto geral. Cada métrica mede um aspecto diferente do modelo.

### Comparação do exemplo

O Gradient Boosting foi escolhido porque obteve a maior **PR-AUC**, que é a métrica principal deste
projeto. A Regressão Logística encontrou uma parcela maior dos cancelamentos (*recall* de 76,5%), mas
o Gradient Boosting teve melhor desempenho geral na identificação da classe minoritária. Essa escolha
e suas limitações são detalhadas em [Avaliação do sistema](avaliacao.md).

## Métricas de aprendizado de máquina

### Acurácia

Proporção de previsões corretas entre todos os casos. Pode ser enganosa em classes desbalanceadas: um modelo
que quase sempre prevê a classe mais comum pode ter acurácia alta e ainda encontrar poucos casos de churn.

### AUC

*Area Under the Curve* ou **área sob a curva**. Resume uma curva de avaliação em um valor. Em geral,
quanto maior o valor, melhor, mas é necessário observar qual curva está sendo medida: PR ou ROC.

### Classe desbalanceada

Situação em que uma categoria aparece bem menos que a outra. Neste conjunto de dados, há menos clientes
com churn do que sem churn. Por isso, olhar somente a acurácia pode dar uma impressão enganosa.

### F1

Média harmônica entre **precisão** e **recall**. É alta somente quando as duas métricas estão razoavelmente
altas. O projeto usa F1 para escolher o limiar de classificação de cada modelo.

### Limiar (`thr` ou *threshold*)

Valor que transforma uma probabilidade em uma decisão. Com limiar `0,34`, por exemplo, um risco calculado
de 40% é classificado como churn e um risco de 30% não é. Diminuir o limiar costuma encontrar mais casos,
mas também pode gerar mais falsos alarmes.

### PR-AUC

Área sob a curva de **precisão × recall** (*Precision–Recall Area Under the Curve*). Mostra como essas duas
métricas se comportam em vários limiares. É especialmente útil quando a classe de interesse, como churn,
é menos frequente. É o principal critério de escolha do modelo neste projeto.

### Precisão (*precision*)

Entre os clientes que o modelo classificou como churn, indica quantos realmente cancelaram. Precisão alta
significa menos falsos alarmes. Não deve ser confundida com acurácia.

### Recall (sensibilidade)

Entre todos os clientes que realmente cancelaram, indica quantos o modelo conseguiu encontrar. Recall alto
significa que poucos casos de churn passaram despercebidos.

### ROC-AUC

Área sob a curva ROC (*Receiver Operating Characteristic*). Mede a capacidade do modelo de atribuir riscos
maiores aos clientes com churn do que aos clientes sem churn, considerando vários limiares. Um valor de
`0,5` equivale aproximadamente a uma ordenação aleatória; `1,0` representa uma separação perfeita.

## Modelos e explicabilidade

### Baseline

Modelo de referência, geralmente mais simples, usado para verificar se uma abordagem mais complexa realmente
traz ganho. A Regressão Logística é o baseline deste projeto.

### Churn

Cancelamento ou abandono do serviço pelo cliente. A aplicação estima a probabilidade de um cliente de
telecom cancelar.

### Gradient Boosting

Método que combina várias árvores de decisão construídas em sequência. Cada nova árvore tenta corrigir
parte dos erros das anteriores. Foi o modelo escolhido pelo projeto por apresentar a maior PR-AUC.

### Regressão Logística (*logistic regression*)

Algoritmo de classificação que estima a probabilidade de uma das duas classes, neste caso churn ou não
churn. Apesar do nome, é usado aqui para classificação.

### SHAP

Técnica de explicabilidade que estima quanto cada característica do cliente aumentou ou reduziu a previsão
de risco. É usada para apresentar os fatores que mais influenciaram uma previsão individual.

## Aplicação e agente

### API

Interface usada por programas para conversar com a aplicação. Por exemplo, `POST /api/predict` recebe os
dados de um cliente e devolve a previsão em formato JSON.

### Fallback

Resposta alternativa usada quando o LLM está indisponível, demora demais ou produz uma saída incoerente.
Ela é determinística e mantém a probabilidade calculada pelo modelo de ML.

### Function calling / ferramenta (*tool*)

Mecanismo que permite ao LLM solicitar a execução de uma função do sistema. Neste projeto, a ferramenta
`predict_churn` chama o modelo de ML e devolve a probabilidade e os fatores SHAP.

### Guardrail

Regra de proteção aplicada à entrada ou à saída do agente. Os guardrails limitam o assunto atendido,
bloqueiam tentativas de manipulação e verificam se a resposta do LLM respeita a previsão calculada.

### JSON / JSONL

**JSON** é um formato de texto estruturado usado nas requisições e respostas da API. **JSONL** guarda um
objeto JSON por linha; o projeto usa esse formato nos registros de monitoramento.

### LLM

*Large Language Model* ou **modelo de linguagem de grande porte**. É o componente que transforma o resultado
numérico em explicação e recomendação. Ele não calcula a probabilidade de churn.

### ML

*Machine Learning* ou **aprendizado de máquina**. Neste projeto, é a parte responsável por aprender com o
histórico de clientes e calcular o risco de churn.

### Pipeline

Sequência padronizada de transformações e etapas do modelo. Garante que os dados recebam o mesmo tratamento
durante o treinamento e durante uma previsão em produção.

### Trace

Registro de uma interação contendo informações como latência, custo estimado, uso de fallback e bloqueios
de guardrail. Ajuda a monitorar e investigar o comportamento da aplicação.

## Infraestrutura e interface

### Build

Processo que prepara a aplicação para execução. Aqui, o build instala dependências, treina o modelo e monta
a imagem Docker.

### CI/CD

Automação de integração e entrega contínuas. O GitHub Actions verifica o código, treina o modelo, executa
os testes e constrói a imagem Docker a cada alteração relevante.

### Container e imagem Docker

A **imagem** é um pacote com a aplicação e suas dependências. O **container** é uma instância dessa imagem
em execução.

### FastAPI, Uvicorn e Jinja2

**FastAPI** define a aplicação web e a API; **Uvicorn** mantém essa aplicação rodando e recebendo requisições;
**Jinja2** monta o HTML da interface a partir de um template.

### HTTP e HTTPS

Protocolos usados para acessar aplicações web. HTTPS adiciona criptografia e autenticação do endereço por
certificado digital.

### UI e UX

**UI** (*User Interface*) é a interface visual usada pela pessoa. **UX** (*User Experience*) é a experiência
mais ampla de uso, incluindo clareza, facilidade e resposta às ações.

### VPS

*Virtual Private Server* ou **servidor virtual privado**. É a máquina remota onde o container da aplicação
pode ser hospedado.
