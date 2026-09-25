# Multi-Agent Ecosystem

Projeto acadêmico **Arquitetura de Integração de Agentes Especialistas em Ambientes Corporativos**.

A proposta é validar uma arquitetura modular para registrar, selecionar, coordenar e auditar capacidades especializadas. A Prova de Conceito usa solicitações técnicas como entrada e mantém o vínculo entre contexto, decisões, chamadas de modelo e eventos por meio de um `Trace ID`.

## Estado atual

A base implementa:

- frontend em React, Vite e TypeScript;
- API em FastAPI com SQLAlchemy;
- PostgreSQL e migrations Alembic;
- autenticação por sessão opaca em cookie `HttpOnly`, por e-mail/senha ou login com GitHub (OAuth, opcional — ver [docs/integrations/github-oauth.md](docs/integrations/github-oauth.md));
- proteção CSRF, rate limiting e auditoria;
- perfis `USER`, `TECHNICIAN`, `REVIEWER` e `ADMIN`;
- criação de solicitações técnicas;
- qualificação inicial do contexto;
- anexo de documentos de texto (código-fonte, markdown, etc.) como contexto adicional de uma solicitação — PDF/DOCX ainda não são suportados;
- geração de `Trace ID`;
- histórico e timeline de eventos;
- abstração de provedores de modelo, com OpenRouter como Model Gateway primário;
- adaptador da OpenAI mantido como integração direta opcional;
- registro de invocações com identificador próprio, hashes, latência e uso de tokens;
- ingestão e recuperação de contexto (RAG) sobre uma base de conhecimento indexada;
- catálogo funcional de Agent Skills, com importação do manifesto `modelo.md` e aprovação humana obrigatória;
- execução de Agent Skills via MCP e avaliação por Quality Gate;
- quatro Agent Skills com executor real (Código Legado, Regras de Negócio, Arquitetura de Software e Segurança da Informação), acionáveis em conjunto numa mesma análise;
- revisão humana de solicitações sinalizadas pelo Quality Gate (perfil `REVIEWER` ou `ADMIN`, aprovação ou rejeição com justificativa, `POST /api/v1/requests/{id}/review`);
- resposta final consolidada (síntese técnica, recomendações, riscos, limitações e agentes participantes), distinta das respostas parciais de cada Agent Skill;
- extensibilidade plug-and-play comprovada: a quarta Agent Skill (Segurança da Informação) foi acoplada sem alteração do núcleo do Orquestrador — evidência em `docs/validation/evidence/2026-08-plug-and-play-extensibility.md`.

Ainda não fazem parte desta base:

- seleção dinâmica de skills (hoje o roteamento é por correspondência exata de domínio — decisão deliberada de escopo);
- publicação automática de artefatos;
- extração de texto de anexos binários (PDF, DOCX) — só texto puro (UTF-8) é aceito hoje.

> O perfil `REVIEWER` não está definido na RFC (a especificação principal do projeto); ele vem de `docs/Documento_de_referencia.md`, um documento à parte com uma visão arquitetural mais ampla. Foi implementado por decisão explícita, fora do escopo formal da RFC v3.1.

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

Login com GitHub é opcional e vem desabilitado por padrão (`GITHUB_OAUTH_ENABLED=false`) — sobe normalmente sem ele, só e-mail/senha continua disponível. Passo a passo pra habilitar: [docs/integrations/github-oauth.md](docs/integrations/github-oauth.md).

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
0012_request_attachments (head)
```

## Fluxo disponível

```text
Usuário autenticado
  -> cria uma solicitação técnica
  -> sistema gera o Trace ID
  -> contexto é avaliado
  -> status fica AWAITING_CONTEXT ou QUALIFIED
  -> eventos são persistidos
  -> dashboard e timeline exibem o histórico
```

A execução exige um usuário autenticado com qualquer papel exceto `REVIEWER` (ver `ORCHESTRATION_ROLES` em `app/core/roles.py` — separação de funções: quem revisa não é quem produz), `LLM_ENABLED=true` e uma `OPENROUTER_API_KEY` válida. O resultado é estruturado e marcado para aprovação humana. A base não executa tools nem publica documentos automaticamente.

### Acesso e cota de uso (três camadas independentes)

São três verificações separadas, aplicadas nesta ordem — cada uma só é avaliada se a anterior já passou:

1. **Papel do usuário** (controla *se* a pessoa pode executar). Todo cadastro novo nasce como `USER` e já consegue executar orquestrações — `USER`, `TECHNICIAN` e `ADMIN` podem; só `REVIEWER` não pode (seu papel é avaliar o que foi produzido, não produzir). Importar/criar uma nova Agent Skill continua restrito a `TECHNICIAN`/`ADMIN` — rodar uma skill já existente é um nível de confiança diferente de decidir quais skills entram no catálogo. Só um `ADMIN` pode promover alguém de papel, pela página `/admin` (menu "ADMINISTRAÇÃO", visível só para quem já é admin) — não existe autopromoção nem fluxo de aprovação automática. A conta admin de bootstrap (`BOOTSTRAP_ADMIN_EMAIL`/`BOOTSTRAP_ADMIN_PASSWORD` no `.env`) é o ponto de partida para promover as primeiras contas.
2. **Visibilidade da Agent Skill** (controla *o que* existe pra executar). Toda skill nova nasce `OFFICIAL` — visível e executável por qualquer usuário autenticado, não só por quem a importou — pra que o catálogo não fique vazio para todo mundo além do `TECHNICIAN`/`ADMIN` que importou cada skill. `owner_id` continua registrado para atribuição/auditoria, mesmo não controlando mais visibilidade por padrão; `visibility="PRIVATE"` ainda existe no modelo para quem quiser registrar uma skill em teste, visível só ao próprio dono (e a `ADMIN`), mas não é o padrão.
3. **Cota diária de tokens** (controla *quanto* uma pessoa já autorizada pode executar naquele dia; desligada por padrão — `LLM_DAILY_TOKEN_LIMIT_PER_USER=0`). Ver [Integração com provedores de modelo](docs/integrations/model-provider.md#cota-diária-de-tokens-por-usuário) para os detalhes — `LLM_DAILY_TOKEN_LIMIT_PER_USER` no `.env`, contas `ADMIN` sempre isentas.

> Como o cadastro é aberto por padrão (`ALLOW_REGISTRATION=true`) e agora `USER` executa sem precisar de promoção, um deploy real exposto publicamente deve considerar reativar a cota diária de tokens (item 3) e/ou fechar o cadastro — sem isso, qualquer pessoa que se cadastre pode gerar chamadas de LLM sem limite algum.

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

## Documentação

- [Visão da arquitetura](docs/architecture/overview.md)
- [Princípios de arquitetura](docs/architecture/principles.md)
- [Integração com provedores de modelo](docs/integrations/model-provider.md)
- [Segurança](SECURITY.md)
- [Evidência de validação da base](docs/validation/evidence/2026-08-foundation-validation.md)
- [Evidência de extensibilidade plug-and-play](docs/validation/evidence/2026-08-plug-and-play-extensibility.md)
- [Primeira medição de KPIs (M7)](docs/validation/evidence/2026-08-m7-kpi-measurement.md)
- [Validação de qualidade do RAG (domínio Código Legado)](docs/validation/evidence/2026-08-30-rag-quality-validation.md)
- [Validação de qualidade do RAG nos 4 domínios de Agent Skill](docs/validation/evidence/2026-09-rag-multi-domain-quality-validation.md)
- [Histórico de mudanças](CHANGELOG.md)

O RFC acadêmico permanece como a especificação principal do projeto. Os documentos deste repositório registram o que já foi implementado e as limitações conhecidas da PoC.
