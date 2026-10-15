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

O painel **"Multi-Agent Ecosystem — Visão geral"** abre como página inicial do Grafana.

`/metrics` fica fora do prefixo `/api`, então o nginx do frontend (porta 3000) não o expõe.

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
