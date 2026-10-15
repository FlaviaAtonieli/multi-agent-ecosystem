# Multi-Agent Ecosystem

[![CI](https://github.com/FlaviaAtonieli/multi-agent-ecosystem/actions/workflows/ci.yml/badge.svg)](https://github.com/FlaviaAtonieli/multi-agent-ecosystem/actions/workflows/ci.yml)

Projeto acadêmico **Arquitetura de Integração de Agentes Especialistas em Ambientes Corporativos**.

A proposta é validar uma arquitetura modular para registrar, selecionar, coordenar e auditar capacidades especializadas. A Prova de Conceito usa solicitações técnicas como entrada e mantém o vínculo entre contexto, decisões, chamadas de modelo e eventos por meio de um `Trace ID`.

## Tecnologias

- **Frontend**: React, Vite, TypeScript.
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, migrations via Alembic.
- **Autenticação**: sessão opaca em cookie `HttpOnly` -- e-mail/senha, GitHub OAuth ou Google OAuth (ambos opcionais).
- **Modelo de IA**: OpenRouter como Model Gateway primário (RAG + LLM), sem provedor mock.
- **Infra**: Docker Compose; guia de deploy no Azure em [docs/deployment/azure.md](docs/deployment/azure.md).

## Capacidades principais

- Solicitação técnica → qualificação de contexto → execução por Agent Skills (RAG + LLM) → Quality Gate → resposta consolidada, tudo rastreado por `Trace ID`.
- Catálogo de 10 domínios de Agent Skill oficiais, extensível por manifesto `modelo.md` sem alterar o núcleo do Orquestrador (evidência: `docs/validation/evidence/2026-08-plug-and-play-extensibility.md`).
- Revisão humana obrigatória de solicitações sinalizadas pelo Quality Gate, feita por quem abriu a solicitação.
- Clãs (grupos auto-serviço) como terceira visibilidade de Agent Skill, ao lado de `OFFICIAL`/`PRIVATE`.
- Página de conta com exclusão lógica (preserva histórico referenciado por outras tabelas).
- CI com análise estática em todo push/PR (`.github/workflows/ci.yml`).

Detalhes de arquitetura, os três níveis de controle de acesso e o que ainda não faz parte da base: [Wiki do projeto](https://github.com/FlaviaAtonieli/multi-agent-ecosystem/wiki) e [SECURITY.md](SECURITY.md#autorização).

> Desde 14/10/2026 não há papéis de usuário: todos têm as mesmas permissões e o acesso é controlado por propriedade (ver [SECURITY.md](SECURITY.md#autorização)).

## Estrutura

```text
multi-agent-ecosystem/
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── agent_catalog/
│   │   ├── agent_manifest/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── llm/
│   │   ├── models/
│   │   ├── quality_gate/
│   │   ├── rag/
│   │   ├── schemas/
│   │   └── services/
│   └── tests/
├── frontend/
│   └── src/
├── docs/
└── docker-compose.yml
```

A PoC começa como um monólito modular. Essa escolha reduz a complexidade operacional e mantém separados os domínios de autenticação, solicitações, orquestração, integração com modelos e auditoria.

## Execução local

Na raiz do projeto, crie o arquivo de ambiente:

```powershell
Copy-Item .env.example .env
```

Defina senhas próprias e mantenha a mesma senha nas duas variáveis do PostgreSQL:

```env
POSTGRES_PASSWORD=defina-uma-senha-local
DATABASE_URL=postgresql+psycopg://agenthub:defina-uma-senha-local@db:5432/agenthub

BOOTSTRAP_ADMIN_EMAIL=admin@agenthub.com
BOOTSTRAP_ADMIN_PASSWORD=defina-outra-senha-forte
```

Não existe provedor mock: para usar a camada de planejamento (LLM) e a recuperação de conhecimento (RAG), é necessária uma `OPENROUTER_API_KEY` real. Sem chave, a aplicação sobe normalmente com `LLM_ENABLED=false` — só a integração de modelo fica indisponível.

```env
LLM_ENABLED=true
LLM_PROVIDER=openrouter
LLM_MODEL=nvidia/nemotron-3-super-120b-a12b:free
OPENROUTER_API_KEY=defina-sua-chave-da-openrouter
```

O modelo acima é gratuito no catálogo da OpenRouter (limite de 50 requisições/dia sem créditos comprados). Crie uma chave em [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys).

Login com GitHub e login com Google são opcionais e vêm desabilitados por padrão (`GITHUB_OAUTH_ENABLED=false`, `GOOGLE_OAUTH_ENABLED=false`) — sobe normalmente sem eles, só e-mail/senha continua disponível. Passo a passo pra habilitar: [docs/integrations/github-oauth.md](docs/integrations/github-oauth.md) e [docs/integrations/google-oauth.md](docs/integrations/google-oauth.md).

Suba os serviços:

```powershell
docker compose up --build -d
```

Acessos locais:

- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/v1/health`

Confira o estado dos containers:

```powershell
docker compose ps
```

Confira a migration aplicada:

```powershell
docker compose exec backend alembic current
```

Na base atual, o resultado esperado é:

```text
0014_google_oauth (head)
```

## Fluxo disponível

```text
Usuário autenticado
  -> cria uma solicitação técnica
  -> contexto é avaliado (AWAITING_CONTEXT ou QUALIFIED)
  -> execução aciona as Agent Skills do(s) domínio(s) pedido(s)
  -> Quality Gate aprova ou sinaliza revisão humana
  -> resposta final consolidada
```

Exige usuário autenticado, `LLM_ENABLED=true` e `OPENROUTER_API_KEY` válida. A base não executa tools nem publica documentos automaticamente. Detalhe completo do fluxo e dos três níveis de controle de acesso (propriedade → visibilidade da skill → cota de tokens): [Wiki do projeto](https://github.com/FlaviaAtonieli/multi-agent-ecosystem/wiki) e [SECURITY.md](SECURITY.md#autorização).

## Testes

A suíte do backend chama a OpenRouter de verdade (sem provedor mock) — exige uma `OPENROUTER_API_KEY` real no ambiente ou no `.env` da raiz do projeto antes de rodar.

Backend:

```powershell
docker run --rm `
  --mount "type=bind,source=$((Get-Location).Path)\backend,target=/app" `
  --env-file .env `
  -w /app `
  python:3.12-slim `
  sh -c "pip install --no-cache-dir -r requirements-dev.txt && pytest -v"
```

Frontend:

```powershell
docker compose build frontend --no-cache
```

## Endereço da aplicação

Ainda não implantada em produção -- guia de deploy (Azure) pronto em [docs/deployment/azure.md](docs/deployment/azure.md), execução pendente.

## Documentação

- [Documentação da API (Swagger/OpenAPI)](docs/api/README.md) — Swagger em `/docs` no desenvolvimento e `docs/api/openapi.json` versionado
- [Monitoramento (Prometheus + Grafana)](docs/monitoring.md) — métricas em `/metrics`, painel pronto em http://localhost:3001
- [Wiki do projeto](https://github.com/FlaviaAtonieli/multi-agent-ecosystem/wiki) — ponto de partida navegável (arquitetura, como rodar, domínios de Agent Skills, segurança, validação)
- [Visão da arquitetura](docs/architecture/overview.md)
- [Princípios de arquitetura](docs/architecture/principles.md)
- [Integração com provedores de modelo](docs/integrations/model-provider.md)
- [Deploy no Azure](docs/deployment/azure.md)
- [Segurança](SECURITY.md)
- [Evidência de validação da base](docs/validation/evidence/2026-08-foundation-validation.md)
- [Evidência de extensibilidade plug-and-play](docs/validation/evidence/2026-08-plug-and-play-extensibility.md)
- [Primeira medição de KPIs (M7)](docs/validation/evidence/2026-08-m7-kpi-measurement.md)
- [Validação de qualidade do RAG (domínio Código Legado)](docs/validation/evidence/2026-08-30-rag-quality-validation.md)
- [Validação de qualidade do RAG nos 4 domínios de Agent Skill](docs/validation/evidence/2026-09-rag-multi-domain-quality-validation.md)
- [Histórico de mudanças](CHANGELOG.md)

O RFC acadêmico permanece como a especificação principal do projeto. Os documentos deste repositório registram o que já foi implementado e as limitações conhecidas da PoC.
