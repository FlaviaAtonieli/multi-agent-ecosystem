# Monitoramento (Prometheus + Grafana)

O backend expõe métricas no formato Prometheus em `GET /metrics`. O `docker compose` sobe um Prometheus, que coleta essas métricas a cada 15 s, e um Grafana já configurado com a fonte de dados e um painel pronto.

## Como usar

```bash
docker compose up -d --build
```

| Serviço | Endereço | Acesso |
|---|---|---|
| Grafana | http://localhost:3001 | `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` do `.env` (padrão `admin` / `change-this-grafana-password`) |
| Prometheus | http://localhost:9090 | sem login; alertas em http://localhost:9090/alerts |
| Métricas cruas | http://localhost:8000/metrics | direto no backend |

O painel **"Flav.IA — Visão geral"** abre como página inicial do Grafana.

`/metrics` fica fora do prefixo `/api`, então o nginx do frontend (porta 3000) não o expõe.

## Monitorar a produção no Azure (24 h)

Prometheus e Grafana rodam numa imagem só (`monitoring/azure/`), como mais um app no **mesmo plano do App Service do backend**. O plano é cobrado pelo plano, não por app, então não há custo a mais enquanto houver memória (B1: 1,75 GB).

```text
Grafana (público, com login) ──> Prometheus (só dentro do contêiner) ──Bearer token──> /metrics do backend
```

- Só o Grafana fica exposto, e pede login. O Prometheus escuta em `127.0.0.1` dentro do contêiner.
- O token de `/metrics` e a senha do Grafana são gerados no Cloud Shell e ficam só nas configurações do App Service.
- A imagem é publicada no `ghcr.io` pelo `publish-images.yml`, junto com a do backend. Na primeira vez, torne o pacote `multi-agent-ecosystem-monitoring` público, como o do backend ([azure.md](azure.md)).

No Cloud Shell (bash):

```bash
RG='Flav.ia'
BACKEND=multi-agent-ecosystem-back
MONITOR=multi-agent-ecosystem-monitor   # se o nome já existir no Azure, troque
PLAN=$(az webapp show -g "$RG" -n "$BACKEND" --query appServicePlanId -o tsv)
BACKEND_HOST=$(az webapp show -g "$RG" -n "$BACKEND" --query defaultHostName -o tsv)
TOKEN=$(openssl rand -hex 32)
GRAFANA_PASSWORD=$(openssl rand -base64 18)

# 1. Liga as métricas no backend e libera só /metrics na autenticação do linked
#    backend. O caminho continua protegido pelo token.
az webapp config appsettings set -g "$RG" -n "$BACKEND" -o none   --settings METRICS_ENABLED=true METRICS_TOKEN="$TOKEN"
az webapp auth update -g "$RG" -n "$BACKEND" --excluded-paths '["/metrics"]' -o none

# 2. Cria o app do monitoramento no mesmo plano.
az webapp create -g "$RG" -n "$MONITOR" --plan "$PLAN" -o none   --deployment-container-image-name ghcr.io/flaviaatonieli/multi-agent-ecosystem-monitoring:latest
MONITOR_HOST=$(az webapp show -g "$RG" -n "$MONITOR" --query defaultHostName -o tsv)
az webapp config appsettings set -g "$RG" -n "$MONITOR" -o none --settings   WEBSITES_PORT=3000 BACKEND_HOST="$BACKEND_HOST" METRICS_TOKEN="$TOKEN"   GF_SECURITY_ADMIN_PASSWORD="$GRAFANA_PASSWORD" GF_SERVER_ROOT_URL="https://$MONITOR_HOST"
# Always On: sem ele, o app dorme sem visitas e o Prometheus para de coletar.
az webapp config set -g "$RG" -n "$MONITOR" --always-on true -o none
az webapp update -g "$RG" -n "$MONITOR" --https-only true -o none

echo "Grafana: https://$MONITOR_HOST (usuário admin)"
echo "Senha do Grafana, guarde num gerenciador de senhas: $GRAFANA_PASSWORD"
```

**Conferir:** no Grafana, o painel "Backend no ar" deve mostrar 1. Em **Explore**, a consulta `up{job="agenthub-backend"}` deve dar 1. Se der 0:
- veja se o Prometheus recebeu `401` (token diferente do backend);
- confira o caminho liberado com `az webapp auth show -g "$RG" -n "$BACKEND"`.

**Memória do plano:** os três apps dividem a memória do B1. Para acompanhar:

```bash
az monitor metrics list --resource "$PLAN" --metric MemoryPercentage --interval PT5M -o table
```

**Limitações:**
- O histórico do Prometheus fica no disco temporário do contêiner e se perde quando o app reinicia.
- O Grafana não guarda nada além do que vem na imagem: o painel e a fonte de dados.

**Para economizar crédito:** desligue e ligue o monitoramento junto com o resto (`az webapp stop` e `az webapp start -g "$RG" -n "$MONITOR"`). Com o backend desligado, o alerta `BackendFora` dispara, e isso é o esperado.

### Alternativa: no seu computador

`docker-compose.azure-monitoring.yml` roda a mesma coleta no seu computador, sem nada novo no Azure. Só coleta enquanto os contêineres estiverem rodando.

No Azure, pelo Cloud Shell:

```bash
TOKEN="$(openssl rand -hex 32)"

# Liga as métricas. O backend reinicia sozinho.
az webapp config appsettings set -g 'Flav.ia' -n multi-agent-ecosystem-back -o none \
  --settings METRICS_ENABLED=true METRICS_TOKEN="$TOKEN"

# O linked backend do Static Web App bloqueia acesso direto ao App Service. Libera só
# este caminho, que continua protegido pelo token.
az webapp auth update -g 'Flav.ia' -n multi-agent-ecosystem-back --excluded-paths '["/metrics"]' -o none

echo "$TOKEN"
```

No seu computador, na raiz do repositório, grave o token e suba os containers. O arquivo fica fora do git:

```powershell
Set-Content -NoNewline -Encoding ascii monitoring/prometheus/metrics_token "COLE-O-TOKEN-AQUI"
docker compose -f docker-compose.azure-monitoring.yml up -d
```

Depois, abra o Grafana em `http://localhost:3001`. Em **Status > Targets**, no Prometheus (`http://localhost:9090`), o job `agenthub-backend` deve aparecer como `UP`.

Se o Prometheus receber `401` da autenticação do Azure, confira o caminho liberado com `az webapp auth show -g 'Flav.ia' -n multi-agent-ecosystem-back`.

## Métricas

Todas começam com `agenthub_`.

### API

| Métrica | Tipo | Labels | O que mede |
|---|---|---|---|
| `http_requests_total` | counter | `method`, `route`, `status` | Requisições atendidas |
| `http_request_duration_seconds` | histogram | `method`, `route` | Latência (buckets até 5 min, por causa da execução da orquestração) |
| `http_requests_in_progress` | gauge | — | Requisições em andamento |

`route` é o template da rota (`/api/v1/requests/{request_id}`), nunca a URL concreta. URLs inexistentes viram `route="unmatched"`. Assim o número de séries não cresce com ids nem com varreduras.

### Orquestração e IA

| Métrica | Tipo | Labels | O que mede |
|---|---|---|---|
| `llm_invocations_total` | counter | `provider`, `model`, `status` | Chamadas ao LLM (`COMPLETED` / `FAILED`) |
| `llm_invocation_duration_seconds` | histogram | `provider`, `model` | Latência das chamadas ao LLM |
| `llm_tokens_total` | counter | `provider`, `model`, `direction` | Tokens de entrada e de saída |
| `agent_skill_invocations_total` | counter | `domain`, `status` | Execuções de Agent Skills |
| `agent_skill_invocation_duration_seconds` | histogram | `domain` | Latência das Agent Skills |
| `quality_gate_verdicts_total` | counter | `outcome` | Veredito do Conselheiro: `approved` (entregue direto) ou `human_review` |
| `human_reviews_total` | counter | `decision` | Revisões humanas (`approve` / `reject`) |
| `agent_response_feedback` | gauge, lido do banco | `domain`, `confidence`, `quality_gate`, `useful` | Avaliações humanas da resposta de cada agente (útil ou não). Painel "Avaliação humana das respostas" |

### Segurança

| Métrica | Tipo | Labels | O que mede |
|---|---|---|---|
| `audit_events_total` | counter | `event_type` | Todo evento de auditoria: `AUTH_LOGIN_SUCCESS`, `AUTH_LOGIN_FAILED`, `AUTH_LOGIN_BLOCKED`, `AUTH_LOGIN_CODE_SENT`, `AUTH_LOGIN_CODE_FAILED`, `AUTH_PASSWORD_RESET_*` etc. |

### Estado do banco (lido a cada coleta)

| Métrica | Tipo | Labels |
|---|---|---|
| `technical_requests` | gauge | `status` |
| `agent_skills_active` | gauge | — |
| `users` | gauge | — |
| `clans` | gauge | — |

Se o banco estiver fora do ar, essas séries somem da coleta, mas o `/metrics` continua respondendo.

## Alertas

Definidos em `monitoring/prometheus/alerts.yml`:

| Alerta | Condição |
|---|---|
| `BackendFora` | Coleta do backend falhando há 1 min |
| `TaxaDeErro5xxAlta` | Mais de 5% de respostas 5xx por 5 min |
| `FalhasNoLLM` | 3+ chamadas ao LLM com falha em 15 min |
| `PossivelForcaBrutaNoLogin` | Mais de 20 falhas de login/código em 10 min |

Os alertas aparecem no Prometheus. Ainda não há Alertmanager para mandar notificações.

## Configuração

| Variável | Padrão | Descrição |
|---|---|---|
| `METRICS_ENABLED` | `true` | Liga o `/metrics` e a coleta |
| `METRICS_TOKEN` | vazio | Se definido, o scrape precisa enviar `Authorization: Bearer <token>`. **Obrigatório em produção**: a aplicação recusa subir sem ele |
| `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` | `admin` / `change-this-grafana-password` | Login do Grafana no compose |

Com `METRICS_TOKEN` definido, grave o mesmo valor em `monitoring/prometheus/metrics_token` (ignorado pelo git) e descomente o bloco `authorization` em `monitoring/prometheus/prometheus.yml`.

## Arquivos

- `backend/app/core/metrics.py`: definição das métricas, middleware HTTP e coletor do banco
- `monitoring/prometheus/prometheus.yml`: coleta; `alerts.yml`: regras
- `monitoring/grafana/provisioning/`: fonte de dados e provedor de painéis
- `monitoring/grafana/dashboards/agenthub-overview.json`: o painel
- `monitoring/azure/`: imagem com Prometheus e Grafana para rodar no App Service (`Dockerfile`, `start.sh`, `prometheus.yml.template`); reaproveita o painel e os alertas acima
