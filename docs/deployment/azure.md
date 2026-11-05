# Deploy no Azure

Arquitetura em produção: o frontend fica em um **Static Web App**, que repassa `/api/*` para o App Service do backend (**linked backend**), sob o mesmo domínio. Isso mantém o cookie de sessão e o CSRF funcionando sem mudar código.

```text
Internet
  -> Azure Static Web App (Standard)   frontend: build do Vite (frontend/dist)
       /api/*  -> linked backend: App Service "backend" (container FastAPI, porta 8000)
                     -> Azure Database for PostgreSQL Flexible Server
```

## Pré-requisitos

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) instalado e autenticado (`az login`).
- Uma assinatura do Azure ativa.
- As imagens Docker publicadas num registro que o App Service consiga puxar. Este guia usa o **GitHub Container Registry** (`ghcr.io`) -- gratuito pra imagem pública, já integra com o GitHub Actions existente (`.github/workflows/ci.yml`) sem precisar de um Azure Container Registry pago à parte (não estava na sua estimativa de custo).

## 1. Variáveis de convenção

Ajuste os nomes abaixo. Nomes de App Service precisam ser **globalmente únicos** em `*.azurewebsites.net`.

```powershell
$RESOURCE_GROUP = "flavia-ia-rg"
$LOCATION = "brazilsouth"
$PLAN_NAME = "flavia-ia-plan"
$BACKEND_APP = "flavia-ia-backend"      # vira flavia-ia-backend.azurewebsites.net
$DB_SERVER = "flavia-ia-db"             # vira flavia-ia-db.postgres.database.azure.com
$DB_NAME = "agenthub"
$DB_ADMIN = "agenthub_admin"
$GHCR_IMAGE_BACKEND = "ghcr.io/flaviaatonieli/multi-agent-ecosystem-backend:latest"
```

## 2. Resource group

```powershell
az group create --name $RESOURCE_GROUP --location $LOCATION
```

## 3. Banco de dados -- Azure Database for PostgreSQL Flexible Server

Tier Burstable (B1ms), o mais barato que ainda serve uma PoC com carga baixa/moderada:

```powershell
az postgres flexible-server create `
  --resource-group $RESOURCE_GROUP `
  --name $DB_SERVER `
  --location $LOCATION `
  --admin-user $DB_ADMIN `
  --admin-password "<senha-forte-aqui>" `
  --sku-name Standard_B1ms `
  --tier Burstable `
  --storage-size 32 `
  --version 16 `
  --database-name $DB_NAME `
  --public-access 0.0.0.0-255.255.255.255
```

> `--public-access 0.0.0.0-255.255.255.255` libera o server pra qualquer IP a nível de firewall do Postgres -- a aplicação ainda exige usuário/senha/TLS pra conectar. Pra restringir de verdade, troque por `--public-access <IP-de-saída-do-App-Service>` depois de descobrir o IP de saída (`az webapp show --query outboundIpAddresses`), ou use VNet Integration (fora do escopo deste guia, mais caro).

O Flexible Server **exige TLS por padrão** -- a `DATABASE_URL` precisa de `?sslmode=require` no final (ver seção de App Settings abaixo).

> **Use só letras e números na senha do banco.** Ela entra na `DATABASE_URL`: um `@` faz a conexão procurar um servidor com nome errado, e um `%` quebra o Alembic. Para gerar uma: `openssl rand -hex 20` com um prefixo em maiúsculas (o Azure exige três tipos de caractere).

Se o servidor já existe e foi criado pelo portal, confira o banco e o acesso:

```bash
az postgres flexible-server db create --resource-group "$RESOURCE_GROUP" --server-name "$DB_SERVER" --name "$DB_NAME"
az postgres flexible-server firewall-rule create --resource-group "$RESOURCE_GROUP" --server-name "$DB_SERVER" --name AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
```

## 4. App Service do backend

```powershell
az appservice plan create `
  --resource-group $RESOURCE_GROUP `
  --name $PLAN_NAME `
  --location $LOCATION `
  --is-linux `
  --sku B1

az webapp create `
  --resource-group $RESOURCE_GROUP `
  --plan $PLAN_NAME `
  --name $BACKEND_APP `
  --deployment-container-image-name $GHCR_IMAGE_BACKEND

az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $BACKEND_APP `
  --settings WEBSITES_PORT=8000
```

### App Settings do backend

Mapeados de `.env.production.example`, com os ajustes específicos do Azure:

Em `ENVIRONMENT=production`, o backend exige `DATABASE_URL` apontando para PostgreSQL; sem essa configuração, o fallback SQLite local é recusado no startup.

```powershell
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $BACKEND_APP --settings `
  ENVIRONMENT=production `
  DATABASE_URL="postgresql+psycopg://$DB_ADMIN`:<senha-forte-aqui>@$DB_SERVER.postgres.database.azure.com:5432/$DB_NAME`?sslmode=require" `
  CORS_ORIGINS="https://<nome>.azurestaticapps.net" `
  TRUSTED_HOSTS="<nome>.azurestaticapps.net,$BACKEND_APP.azurewebsites.net" `
  COOKIE_SECURE=true `
  SESSION_TTL_HOURS=8 `
  ALLOW_REGISTRATION=false `
  AUTO_CREATE_TABLES=false `
  BOOTSTRAP_ADMIN_NAME="<seu nome>" `
  BOOTSTRAP_ADMIN_EMAIL="<seu-email>" `
  BOOTSTRAP_ADMIN_PASSWORD="<senha-forte-aqui>" `
  FRONTEND_BASE_URL="https://<nome>.azurestaticapps.net" `
  LLM_ENABLED=true `
  LLM_PROVIDER=openrouter `
  OPENROUTER_API_KEY="<sua-chave-openrouter>" `
  LOGIN_EMAIL_CODE_ENABLED=false `
  METRICS_ENABLED=false `
  GITHUB_OAUTH_ENABLED=false `
  GOOGLE_OAUTH_ENABLED=false `
  EMAIL_BACKEND=smtp `
  SMTP_HOST=smtp.gmail.com `
  SMTP_USERNAME="<seu-gmail>" `
  SMTP_PASSWORD="<senha-de-app-do-gmail>" `
  SMTP_FROM="<seu-gmail>" `
  METRICS_TOKEN="<gere-com-openssl-rand-hex-32>"
```

> **`METRICS_TOKEN` é obrigatório em produção.** Sem ele a aplicação recusa subir, porque `/metrics` ficaria público no App Service. Para coletar as métricas no Azure, aponte um Prometheus (ou o Azure Monitor managed Prometheus) para `https://<backend>/metrics` com `Authorization: Bearer <token>`. Ver [docs/monitoring.md](../monitoring.md).

> **SMTP é obrigatório em produção.** O login em navegador novo envia um código por e-mail, e com `ENVIRONMENT=production` a aplicação recusa subir com `EMAIL_BACKEND=console`. No Gmail, a senha de app é gerada em https://myaccount.google.com/apppasswords (exige verificação em 2 etapas na conta).

> **`TRUSTED_PROXY_IPS` fica de fora de propósito.** Esse ajuste (`app/core/rate_limit.py::resolve_client_ip`) espera uma lista fixa de IPs de proxy confiável -- funciona bem com o `nginx` do `docker compose` local (IP interno estável), mas não tem um equivalente direto e estável no App Service atrás do Static Web App (o IP que chega "direto" no container já passou pela infraestrutura do Azure antes). Gap conhecido: sem isso configurado, o rate limiter por IP enxerga o IP de borda do Azure pra todo mundo em vez do IP de cada usuário real -- não quebra a aplicação, mas o rate limit deixa de distinguir usuários individuais. Registrado aqui, não resolvido neste guia (é mudança de código, não de infraestrutura).

**A aplicação não sobe em produção sem estas duas decisões:** o código de login por e-mail exige SMTP, e as métricas exigem `METRICS_TOKEN`. Os valores acima desligam os dois para o primeiro deploy. Para ligar depois, veja `.env.production.example`.

`BOOTSTRAP_ADMIN_PASSWORD` precisa ter pelo menos 12 caracteres, com maiúscula, minúscula, número e símbolo, senão o backend não inicia. Ela só vale na criação da conta: mudar a variável depois não altera a senha.

Substitua `<senha-forte-aqui>`, `<nome>.azurestaticapps.net`, `<sua-chave-openrouter>` etc. pelos valores reais. `GITHUB_OAUTH_ENABLED`/`GOOGLE_OAUTH_ENABLED` ficam `false` até você cadastrar os OAuth Apps com o domínio real -- ver checklist no final.

## 5. Imagem do backend no GitHub Container Registry

O workflow `.github/workflows/publish-images.yml` publica a imagem no `ghcr.io` a cada push na `main`, com o `GITHUB_TOKEN` padrão. Depois da primeira publicação, torne o pacote público em **github.com/FlaviaAtonieli?tab=packages → pacote → Package settings → Change visibility → Public**, para o App Service baixar a imagem sem credencial.

## 6. Frontend no Static Web App

- **Workflow:** `.github/workflows/azure-static-web-apps-*.yml`, criado pelo portal ao criar o recurso e ajustado depois. Ele publica `frontend/dist` a cada push na `main`. O token de deploy fica no secret `AZURE_STATIC_WEB_APPS_API_TOKEN_*`, que o portal já criou.
- **Configuração:** `frontend/public/staticwebapp.config.json` manda as rotas da SPA (`/login`, `/reset-password`, ...) para o `index.html` e aplica os cabeçalhos de segurança (CSP, `X-Frame-Options` etc.).

Passos no Azure:

1. **Plano:** o Static Web App precisa estar no plano **Standard**. O Free não aceita linked backend.
2. **Linked backend:** no Static Web App, menu **APIs**, ambiente de produção, **Link**, tipo **Web App**, escolher `$BACKEND_APP`.
3. **Domínio:** `TRUSTED_HOSTS` leva os dois nomes porque a documentação do Static Web Apps não diz qual cabeçalho `Host` o proxy repassa. Depois de confirmar nos logs qual deles chega, dá para deixar só esse.
4. **OAuth:** as URLs de callback do GitHub e do Google são `https://<nome>.azurestaticapps.net/api/v1/auth/{github,google}/callback`. As variáveis `*_OAUTH_REDIRECT_URI` precisam bater exatamente com elas.

## 7. Subir o backend

```powershell
az webapp restart --resource-group $RESOURCE_GROUP --name $BACKEND_APP
```

O `CMD` do `backend/Dockerfile` já roda `alembic upgrade head` antes de subir o `uvicorn` -- as migrations aplicam sozinhas no primeiro start, sem passo manual. A conta inicial (`BOOTSTRAP_ADMIN_*`) também é criada automaticamente no primeiro start, se ainda não existir.

> Se o container falhar ao iniciar, o Azure **para o site** depois de algumas tentativas, e o `az webapp restart` não o religa: use `az webapp start`. Um `403 Web App - Unavailable` indica site parado.

### Cadastrar as Agent Skills e a base de conhecimento

O catálogo e a base de conhecimento começam vazios. Os dois comandos são idempotentes e podem rodar do Cloud Shell, que é aceito pela regra `AllowAzureServices` do banco:

```bash
git clone --depth 1 https://github.com/FlaviaAtonieli/multi-agent-ecosystem.git && cd multi-agent-ecosystem/backend
python3 -m venv ~/venv && ~/venv/bin/pip install -q -r requirements.txt

config() { az webapp config appsettings list -g "$RESOURCE_GROUP" -n "$BACKEND_APP" --query "[?name=='$1'].value | [0]" -o tsv; }
export DATABASE_URL="$(config DATABASE_URL)" BOOTSTRAP_ADMIN_EMAIL="$(config BOOTSTRAP_ADMIN_EMAIL)" OPENROUTER_API_KEY="$(config OPENROUTER_API_KEY)"
export ENVIRONMENT=development AUTO_CREATE_TABLES=false LLM_ENABLED=false

~/venv/bin/python -m app.db.seed_agent_skills
~/venv/bin/python -m app.db.seed_knowledge_base
```

A base de conhecimento usa um modelo de embeddings pago da OpenRouter.

Confira os logs se algo não subir:

```powershell
az webapp log tail --resource-group $RESOURCE_GROUP --name $BACKEND_APP
```

## 8. Deploy automático do backend

A cada push na `main`, o workflow `Publish images` publica a imagem e, se o segredo `AZURE_BACKEND_DEPLOY_WEBHOOK` existir, chama o webhook de implantação contínua do App Service, que baixa a imagem nova e reinicia o container. Sem o segredo, o job termina com um aviso, e o redeploy continua manual (`az webapp restart`).

Rode uma vez, no Cloud Shell:

```bash
# O webhook usa as credenciais de publicação do site (SCM).
az resource update --resource-group "$RESOURCE_GROUP" --namespace Microsoft.Web --resource-type basicPublishingCredentialsPolicies --name scm --parent "sites/$BACKEND_APP" --set properties.allow=true -o none
az webapp deployment container config --enable-cd true --resource-group "$RESOURCE_GROUP" --name "$BACKEND_APP" --query CI_CD_URL -o tsv
```

Copie a URL impressa para um segredo do repositório chamado `AZURE_BACKEND_DEPLOY_WEBHOOK` (**Settings > Secrets and variables > Actions**). **A URL contém a senha de publicação do site:** trate-a como senha e não a coloque em logs, issues ou mensagens.

**Site parado:** ao religar com `az webapp start`, ele baixa a imagem mais recente, mesmo que o deploy tenha acontecido enquanto estava parado.

**Voltar para uma versão anterior:** toda imagem também é publicada com o SHA do commit. Fixe a versão desejada e reinicie:

```bash
az webapp config container set --resource-group "$RESOURCE_GROUP" --name "$BACKEND_APP" --container-image-name "ghcr.io/flaviaatonieli/multi-agent-ecosystem-backend:<sha-do-commit>"
az webapp restart --resource-group "$RESOURCE_GROUP" --name "$BACKEND_APP"
```

Enquanto a versão estiver fixada, os deploys automáticos reinstalam essa mesma imagem. Para voltar a acompanhar a `main`, repita o comando com a tag `latest`.

Uma migration já aplicada não é desfeita ao voltar a imagem: se a versão anterior não for compatível com o banco, rode `alembic downgrade` antes.

## Limitações conhecidas

- **Limite de 45 segundos por chamada à API.** O Static Web Apps corta qualquer requisição a `/api` depois de 45 s, e esse limite não pode ser mudado. Por isso, o site inicia a orquestração por `POST /agent-skills/requests/{id}/start`, que responde na hora e roda as skills em segundo plano, e acompanha o andamento pela linha do tempo. Cada skill levou cerca de 40 s em média (medição de 11/2026, com `openai/gpt-5-mini`), e até `ORCHESTRATION_MAX_PARALLEL_SKILLS` skills rodam ao mesmo tempo (3 por padrão). As perguntas de acompanhamento seguem o mesmo caminho, por `/ask/start`.
- **Um único processo no backend.** A execução em segundo plano vive no processo do backend. Se ele reiniciar, as execuções em andamento são marcadas como `FAILED` e podem ser repetidas pela tela. Por isso, o container não pode rodar com mais de um worker do `uvicorn`, nem o App Service com mais de uma instância.
- **O backend fica acessível só pelo Static Web App.** Ao ligar o linked backend, o Azure adiciona ao App Service um provedor de identidade chamado "Azure Static Web Apps (Linked)", que bloqueia acesso direto a `*.azurewebsites.net`. Isso também bloqueia um Prometheus externo tentando ler `/metrics` direto no App Service. Para coletar métricas, é preciso liberar esse caminho na autenticação do App Service (ver [docs/monitoring.md](../monitoring.md)).
- **Sem pré-visualização por PR.** Os ambientes de PR do Static Web Apps não aceitam linked backend, por isso o workflow só publica a partir da `main`.
- **`TRUSTED_PROXY_IPS`:** ver a ressalva da seção 4. O rate limit por IP enxerga o IP da infraestrutura do Azure.

## Checklist pós-deploy

- [ ] Confirmar que `https://<nome>.azurestaticapps.net/api/v1/health` responde `200`.
- [ ] Confirmar que `https://<nome>.azurestaticapps.net/` carrega o frontend.
- [ ] Cadastrar o OAuth App do GitHub e o OAuth Client do Google com o domínio real (`docs/integrations/github-oauth.md`, `docs/integrations/google-oauth.md`).
- [ ] Depois de cadastrados: `az webapp config appsettings set` no `$BACKEND_APP` com `GITHUB_OAUTH_ENABLED=true`/`GOOGLE_OAUTH_ENABLED=true` e os `*_CLIENT_ID`/`*_CLIENT_SECRET` reais.
- [ ] `ALLOW_REGISTRATION=false` depois do cadastro inicial dos usuários reais.
