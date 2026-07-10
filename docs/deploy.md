# Deploy na sua VPS (EasyPanel)

Guia passo a passo para hospedar o sistema numa VPS usando **EasyPanel**. O projeto é um único
container Docker; o FastAPI serve a UI em `/` e a API em `/api/*`, enquanto o EasyPanel coloca um
proxy (Traefik) na frente e cuida do domínio e do HTTPS.

```
Internet ──HTTPS──▶ Traefik (EasyPanel) ──▶ container (FastAPI/uvicorn) ─┬─ GET /   → UI (HTML/JS)
                                                                        └─ /api/*  → API JSON
```

## Pré-requisitos

- [x] VPS com **EasyPanel** instalado e acessível.
- [x] Um **domínio** (ou subdomínio) com registro **A** apontando para o **IP da VPS**
      (ex.: `churn.seudominio.com` → `A` → IP).
- [x] Repositório no **GitHub** (push feito).
- [x] Sua **`OPENAI_API_KEY`** (opcional — sem ela o sistema roda em modo *fallback*).
- [x] Recomendado: VPS com **≥ 2 GB de RAM** (o build instala scikit-learn/shap).

---

## Opção A — Build a partir do GitHub (recomendado)

!!! info "EasyPanel usa o `Dockerfile`, não o `docker-compose`"
    Cada serviço no EasyPanel constrói **um `Dockerfile` → um container**; ele **ignora** o
    `docker-compose.yml` (que serve só para rodar tudo localmente com um comando). Isso funciona aqui
    porque o nosso `Dockerfile` é **auto-contido**: um único processo (`uvicorn`) serve a UI e a API
    no mesmo container. Ou seja, não há vários serviços para orquestrar.

### 1. Criar o projeto e o serviço
1. No EasyPanel: **Create Project** → dê um nome (ex.: `churn`).
2. Dentro do projeto: **+ Service** → **App**.

### 2. Configurar a fonte (Source)
Na aba **Source**, escolha **GitHub** (conecte a conta/repo) ou **Git** (URL pública):

| Campo | Valor |
|---|---|
| Repository / URL | seu repositório |
| Branch / Ref | `main` (ou `feat/lucas-guimaraes`) |
| **Build Path** | `/` (raiz do repositório) |

!!! note "Build Path"
    O `Dockerfile` fica na **raiz do repositório** e faz `COPY . .`. Deixe o Build Path como `/`
    (é o padrão) — o `python -m ml.train` roda no build a partir daí.

### 3. Build
Na aba **Build**, selecione **Dockerfile** (o EasyPanel detecta o `Dockerfile` automaticamente na
Build Path). Não precisa mexer em mais nada — o `Dockerfile` já treina o modelo no build.

### 4. Variáveis de ambiente
Na aba **Environment**, adicione:

```env
OPENAI_API_KEY=sk-sua-chave-aqui
OPENAI_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=20
```

(Sem `OPENAI_API_KEY`, a aplicação sobe e responde em modo *fallback* — útil pra testar antes.)

### 5. Domínio e porta
Na aba **Domains**:
1. **Add Domain** → informe seu domínio (ex.: `churn.seudominio.com`).
2. Defina a **porta interna** do container como **`7860`** (é a porta que o uvicorn expõe).
3. Ative **HTTPS** (o EasyPanel gera o certificado Let's Encrypt automaticamente).

### 6. Deploy
Clique em **Deploy**. Acompanhe os logs do build (o treino do modelo aparece: `[gradient_boosting] PR-AUC=...`).
Veja [como interpretar o log de treinamento](glossario.md#como-ler-o-log-de-treinamento).
Na primeira vez leva alguns minutos (instalação das dependências).

### 7. Verificar
Depois que subir:

```bash
curl https://churn.seudominio.com/api/health
# {"status":"ok","model_ready":true}
```

- Produto: `https://churn.seudominio.com/`
- API (docs): `https://churn.seudominio.com/api/docs`

---

## Opção B — Deploy de imagem pronta (sem build na VPS)

Útil se a VPS for pequena e você não quiser buildar nela.

1. Faça o build e o push da imagem para um registry (na sua máquina ou via CI):
   ```bash
   cd churn-predictor
   docker build -t ghcr.io/SEU_USUARIO/churn-agent:latest .
   docker push ghcr.io/SEU_USUARIO/churn-agent:latest
   ```
2. No EasyPanel: **+ Service → App → Source = Docker Image** → informe a imagem.
3. Repita os passos **4 (variáveis de ambiente)**, **5 (domínio e porta)** e **6 (deploy)** da Opção A.

---

## Opcionais recomendados

### Persistir os traces de monitoramento
O log de traces (`monitoring/traces.jsonl`) é efêmero e some a cada redeploy. Para mantê-lo:

1. Na aba **Mounts / Volumes**, crie um **Volume** montado em `/app/monitoring`.
2. (Opcional) defina `TRACE_LOG_PATH=/app/monitoring/traces.jsonl` (já é o padrão no container).

### Auto-deploy a cada push
Em **Source**, ative o **webhook** do GitHub (o EasyPanel fornece a URL). Assim, todo push na branch
configurada dispara um novo deploy.

### Healthcheck
O `Dockerfile` já define um `HEALTHCHECK` batendo em `/api/health` — o EasyPanel mostra o status de
saúde do serviço no painel.

---

!!! note "A documentação é publicada no GitHub Pages"
    Esta doc **não** precisa ser hospedada na VPS: o workflow
    [`.github/workflows/docs.yml`](https://github.com/lcsgborges/churn-predictor/blob/main/.github/workflows/docs.yml)
    builda o MkDocs e publica no **GitHub Pages** a cada push na `main`. O `ci.yml` também roda
    `mkdocs build --strict` para pegar links ou nav quebrados antes de publicar.

## Solução de problemas

| Sintoma | Causa provável | Correção |
|---|---|---|
| Build falha em `python -m ml.train` | Build Path apontando para subpasta errada | Defina Build Path = `/` (raiz do repo) |
| `502 Bad Gateway` no domínio | Porta interna incorreta | Confira o valor indicado no passo 5 |
| App responde mas sempre em *fallback* | `OPENAI_API_KEY` ausente/inválida | Configure a env e faça redeploy |
| Build sem memória / muito lento | VPS com pouca RAM | Use a **Opção B** (imagem pronta) |
| Página em branco / 404 nos `/api/*` | Rota ou proxy incorretos | Confira o domínio no EasyPanel e as rotas da aplicação |
