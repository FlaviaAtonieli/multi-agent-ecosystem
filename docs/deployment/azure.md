# Deploy no Azure

Arquitetura alvo (a mesma da estimativa de custo feita na calculadora do Azure): **Azure Front Door** na frente, roteando por path pra dois **App Service** (backend e frontend, Web App for Containers), com **Azure Database for PostgreSQL Flexible Server** como banco.

```text
Internet
  -> Azure Front Door (domínio custom, TLS gerenciado, roteamento por path)
       /api/*  -> App Service "backend"  (container FastAPI, porta 8000)
       /*      -> App Service "frontend" (container nginx+Vite, porta 80)
                     -> Azure Database for PostgreSQL Flexible Server
```

Front Door faz o roteamento que hoje o `nginx.conf` local faz via `proxy_pass http://backend:8000/` (esse hostname só existe na rede interna do `docker compose` -- não existe equivalente dentro do Azure, por isso o Front Door assume esse papel). Os dois App Services ficam com **Access Restriction** pra só aceitar tráfego vindo do Front Door -- as URLs públicas `*.azurewebsites.net` não ficam acessíveis direto.

Registro de aplicativo OAuth (GitHub/Google) fica pra depois do domínio estar no ar -- ver "Checklist pós-deploy" no final.

## Pré-requisitos

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) instalado e autenticado (`az login`).
- Uma assinatura do Azure ativa.
- As imagens Docker publicadas num registro que o App Service consiga puxar. Este guia usa o **GitHub Container Registry** (`ghcr.io`) -- gratuito pra imagem pública, já integra com o GitHub Actions existente (`.github/workflows/ci.yml`) sem precisar de um Azure Container Registry pago à parte (não estava na sua estimativa de custo).

## 1. Variáveis de convenção

Ajuste os nomes abaixo -- nomes de App Service precisam ser **globalmente únicos** em `*.azurewebsites.net`.

```powershell
$RESOURCE_GROUP = "flavia-ia-rg"
$LOCATION = "brazilsouth"
$PLAN_NAME = "flavia-ia-plan"
$BACKEND_APP = "flavia-ia-backend"      # vira flavia-ia-backend.azurewebsites.net
$FRONTEND_APP = "flavia-ia-frontend"    # vira flavia-ia-frontend.azurewebsites.net
$DB_SERVER = "flavia-ia-db"             # vira flavia-ia-db.postgres.database.azure.com
$DB_NAME = "agenthub"
$DB_ADMIN = "agenthub_admin"
$FRONTDOOR_PROFILE = "flavia-ia-fd"
$GHCR_IMAGE_BACKEND = "ghcr.io/flaviaatonieli/multi-agent-ecosystem-backend:latest"
$GHCR_IMAGE_FRONTEND = "ghcr.io/flaviaatonieli/multi-agent-ecosystem-frontend:latest"
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

## 4. App Service Plan + os dois Web Apps for Containers

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

az webapp create `
  --resource-group $RESOURCE_GROUP `
  --plan $PLAN_NAME `
  --name $FRONTEND_APP `
  --deployment-container-image-name $GHCR_IMAGE_FRONTEND
```

Os dois Web Apps compartilham o mesmo Plano (B1 = 1 núcleo, 1.75 GB RAM) -- sem custo adicional por ter dois apps no mesmo plano, igual à sua estimativa mostrou.

### Porta de cada container

```powershell
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $BACKEND_APP `
  --settings WEBSITES_PORT=8000

az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $FRONTEND_APP `
  --settings WEBSITES_PORT=80
```

### App Settings do backend

Mapeados de `.env.production.example`, com os ajustes específicos do Azure:

```powershell
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $BACKEND_APP --settings `
  ENVIRONMENT=production `
  DATABASE_URL="postgresql+psycopg://$DB_ADMIN`:<senha-forte-aqui>@$DB_SERVER.postgres.database.azure.com:5432/$DB_NAME`?sslmode=require" `
  CORS_ORIGINS="https://<seu-dominio-ou-endpoint-do-frontdoor>" `
  TRUSTED_HOSTS="<seu-dominio-ou-endpoint-do-frontdoor>" `
  COOKIE_SECURE=true `
  SESSION_TTL_HOURS=8 `
  ALLOW_REGISTRATION=false `
  AUTO_CREATE_TABLES=false `
  BOOTSTRAP_ADMIN_NAME="<seu nome>" `
  BOOTSTRAP_ADMIN_EMAIL="<seu-email>" `
  BOOTSTRAP_ADMIN_PASSWORD="<senha-forte-aqui>" `
  FRONTEND_BASE_URL="https://<seu-dominio-ou-endpoint-do-frontdoor>" `
  LLM_ENABLED=true `
  LLM_PROVIDER=openrouter `
  OPENROUTER_API_KEY="<sua-chave-openrouter>" `
  GITHUB_OAUTH_ENABLED=false `
  GOOGLE_OAUTH_ENABLED=false
```

> **`TRUSTED_PROXY_IPS` fica de fora de propósito.** Esse ajuste (`app/core/rate_limit.py::resolve_client_ip`) espera uma lista fixa de IPs de proxy confiável -- funciona bem com o `nginx` do `docker compose` local (IP interno estável), mas não tem um equivalente direto e estável no App Service atrás do Front Door (o IP que chega "direto" no container já passou pela infraestrutura do Azure antes). Gap conhecido: sem isso configurado, o rate limiter por IP enxerga o IP de borda do Azure pra todo mundo em vez do IP de cada usuário real -- não quebra a aplicação, mas o rate limit deixa de distinguir usuários individuais atrás do Front Door. Registrado aqui, não resolvido neste guia (é mudança de código, não de infraestrutura).

Substitua `<senha-forte-aqui>`, `<seu-dominio-ou-endpoint-do-frontdoor>`, `<sua-chave-openrouter>` etc. pelos valores reais. `GITHUB_OAUTH_ENABLED`/`GOOGLE_OAUTH_ENABLED` ficam `false` até você cadastrar os OAuth Apps com o domínio real -- ver checklist no final.

### App Settings do frontend

A imagem do frontend já embute `VITE_API_URL=/api/v1` (relativo) desde o build -- nenhuma App Setting de runtime muda isso, porque é uma variável de **build-time** do Vite, não de execução. Caminho relativo funciona porque o Front Door serve os dois App Services sob o mesmo domínio público, roteando `/api/*` pro backend -- sem isso, seria preciso rebuildar a imagem do frontend com uma URL absoluta.

## 5. Publicar as imagens no GitHub Container Registry

O workflow de CI já builda as imagens (`docker compose build`); falta publicar no `ghcr.io`. Via GitHub Actions, autenticando com o `GITHUB_TOKEN` padrão (sem secret novo):

```yaml
# .github/workflows/publish-images.yml (exemplo -- ver arquivo real criado nesta mudança)
- uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
- run: docker build -t ghcr.io/${{ github.repository_owner }}/multi-agent-ecosystem-backend:latest backend
- run: docker push ghcr.io/${{ github.repository_owner }}/multi-agent-ecosystem-backend:latest
```

Depois de publicada ao menos uma vez, torne o pacote público em **github.com/FlaviaAtonieli?tab=packages → pacote → Package settings → Change visibility → Public** -- assim o App Service puxa sem precisar de credencial de registro.

## 6. Azure Front Door (Classic) -- roteamento por path

```powershell
az afd profile create --resource-group $RESOURCE_GROUP --profile-name $FRONTDOOR_PROFILE --sku Standard_AzureFrontDoor

az afd endpoint create --resource-group $RESOURCE_GROUP --profile-name $FRONTDOOR_PROFILE `
  --endpoint-name flavia-ia --enabled-state Enabled

# Origin group + origin do backend
az afd origin-group create --resource-group $RESOURCE_GROUP --profile-name $FRONTDOOR_PROFILE `
  --origin-group-name backend-origins --probe-request-type GET --probe-protocol Https `
  --probe-path /api/v1/health --probe-interval-in-seconds 30 `
  --sample-size 4 --successful-samples-required 3

az afd origin create --resource-group $RESOURCE_GROUP --profile-name $FRONTDOOR_PROFILE `
  --origin-group-name backend-origins --origin-name backend `
  --host-name "$BACKEND_APP.azurewebsites.net" --origin-host-header "$BACKEND_APP.azurewebsites.net" `
  --http-port 80 --https-port 443 --priority 1 --weight 1000 --enabled-state Enabled

# Origin group + origin do frontend
az afd origin-group create --resource-group $RESOURCE_GROUP --profile-name $FRONTDOOR_PROFILE `
  --origin-group-name frontend-origins --probe-request-type GET --probe-protocol Https `
  --probe-path / --probe-interval-in-seconds 30 --sample-size 4 --successful-samples-required 3

az afd origin create --resource-group $RESOURCE_GROUP --profile-name $FRONTDOOR_PROFILE `
  --origin-group-name frontend-origins --origin-name frontend `
  --host-name "$FRONTEND_APP.azurewebsites.net" --origin-host-header "$FRONTEND_APP.azurewebsites.net" `
  --http-port 80 --https-port 443 --priority 1 --weight 1000 --enabled-state Enabled

# Rota /api/* -> backend
az afd route create --resource-group $RESOURCE_GROUP --profile-name $FRONTDOOR_PROFILE `
  --endpoint-name flavia-ia --route-name api-route --origin-group backend-origins `
  --supported-protocols Https --patterns-to-match "/api/*" --forwarding-protocol HttpsOnly `
  --link-to-default-domain Enabled

# Rota default / -> frontend
az afd route create --resource-group $RESOURCE_GROUP --profile-name $FRONTDOOR_PROFILE `
  --endpoint-name flavia-ia --route-name default-route --origin-group frontend-origins `
  --supported-protocols Https --patterns-to-match "/*" --forwarding-protocol HttpsOnly `
  --link-to-default-domain Enabled
```

Isso já dá um domínio público do tipo `flavia-ia-xxxx.z01.azurefd.net`, com TLS gerenciado pelo Azure. Domínio próprio (`seu-dominio.com`) é um passo opcional adicional (`az afd custom-domain create` + validação de DNS) -- não incluído aqui pra manter o guia no escopo do que a estimativa de custo cobre.

## 7. Travar os App Services pra só aceitarem tráfego do Front Door

```powershell
az webapp config access-restriction add --resource-group $RESOURCE_GROUP --name $BACKEND_APP `
  --rule-name AllowFrontDoor --priority 100 --service-tag AzureFrontDoor.Backend `
  --http-header "x-azure-fdid=<ID-do-seu-perfil-Front-Door>"

az webapp config access-restriction add --resource-group $RESOURCE_GROUP --name $FRONTEND_APP `
  --rule-name AllowFrontDoor --priority 100 --service-tag AzureFrontDoor.Backend `
  --http-header "x-azure-fdid=<ID-do-seu-perfil-Front-Door>"
```

O `<ID-do-seu-perfil-Front-Door>` sai de `az afd profile show --resource-group $RESOURCE_GROUP --profile-name $FRONTDOOR_PROFILE --query "frontDoorId"`. Esse header extra evita que outro cliente do Azure (com um Front Door próprio, também usando o service tag genérico) consiga rotear tráfego pro seu App Service.

## 8. Subir os containers

```powershell
az webapp restart --resource-group $RESOURCE_GROUP --name $BACKEND_APP
az webapp restart --resource-group $RESOURCE_GROUP --name $FRONTEND_APP
```

O `CMD` do `backend/Dockerfile` já roda `alembic upgrade head` antes de subir o `uvicorn` -- a migration até `0014_google_oauth` aplica sozinha no primeiro start, sem passo manual. O usuário `ADMIN` de bootstrap (`BOOTSTRAP_ADMIN_*`) também é criado automaticamente no primeiro start, se ainda não existir.

Confira os logs se algo não subir:

```powershell
az webapp log tail --resource-group $RESOURCE_GROUP --name $BACKEND_APP
```

## Checklist pós-deploy

- [ ] Confirmar `https://<endpoint-do-frontdoor>/api/v1/health` responde `200`.
- [ ] Confirmar `https://<endpoint-do-frontdoor>/` carrega o frontend.
- [ ] Cadastrar o OAuth App do GitHub e o OAuth Client do Google com o domínio real do Front Door (`docs/integrations/github-oauth.md`, `docs/integrations/google-oauth.md`) -- as `*_OAUTH_REDIRECT_URI` precisam bater exatamente com `https://<endpoint-do-frontdoor>/api/v1/auth/{github,google}/callback`.
- [ ] Depois de cadastrados: `az webapp config appsettings set` no `$BACKEND_APP` com `GITHUB_OAUTH_ENABLED=true`/`GOOGLE_OAUTH_ENABLED=true` + os `*_CLIENT_ID`/`*_CLIENT_SECRET` reais.
- [ ] Revisar `TRUSTED_PROXY_IPS` (ver nota na seção 4) antes de expor o sistema a usuários reais, se o rate limit por IP individual for importante pro seu caso de uso.
- [ ] `ALLOW_REGISTRATION=false` depois do cadastro inicial dos usuários reais (já no template).
