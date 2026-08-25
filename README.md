# Multi-Agent Ecosystem

Projeto acadêmico **Arquitetura de Integração de Agentes Especialistas em Ambientes Corporativos**.

A proposta é validar uma arquitetura modular para registrar, selecionar, coordenar e auditar capacidades especializadas. A Prova de Conceito usa solicitações técnicas como entrada e mantém o vínculo entre contexto, decisões, chamadas de modelo e eventos por meio de um `Trace ID`.

## Estado atual

A base implementa:

- frontend em React, Vite e TypeScript;
- API em FastAPI com SQLAlchemy;
- PostgreSQL e migrations Alembic;
- autenticação por sessão opaca em cookie `HttpOnly`;
- proteção CSRF, rate limiting e auditoria;
- perfis `USER`, `TECHNICIAN`, `REVIEWER` e `ADMIN`;
- criação de solicitações técnicas;
- qualificação inicial do contexto;
- geração de `Trace ID`;
- histórico e timeline de eventos;
- abstração de provedores de modelo;
- provedor `mock` para testes sem chamada externa;
- adaptador da OpenAI desabilitado por padrão;
- registro de invocações com identificador próprio, hashes, latência e uso de tokens;
- ingestão e recuperação de contexto (RAG) sobre uma base de conhecimento indexada;
- catálogo funcional de Agent Skills, com importação do manifesto `modelo.md` e aprovação humana obrigatória;
- execução de Agent Skills via MCP e avaliação por Quality Gate;
- três Agent Skills com executor real (Código Legado, Regras de Negócio e Arquitetura de Software), acionáveis em conjunto numa mesma análise;
- revisão humana de solicitações sinalizadas pelo Quality Gate (perfil `REVIEWER` ou `ADMIN`, aprovação ou rejeição com justificativa, `POST /api/v1/requests/{id}/review`).

Ainda não fazem parte desta base:

- seleção dinâmica de skills (hoje o roteamento é por correspondência exata de domínio — decisão deliberada de escopo);
- publicação automática de artefatos.

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

A integração externa deve permanecer desabilitada na primeira execução:

```env
LLM_ENABLED=false
LLM_PROVIDER=mock
OPENAI_API_KEY=
```

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
0003_llm_foundation (head)
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

O provedor simulado pode ser habilitado para validar a camada de planejamento sem chave externa:

```env
LLM_ENABLED=true
LLM_PROVIDER=mock
```

A execução exige um usuário com perfil `TECHNICIAN` ou `ADMIN`. O resultado é estruturado e marcado para aprovação humana. A base não executa tools nem publica documentos automaticamente.

## Testes

Backend:

```powershell
docker run --rm `
  --mount "type=bind,source=$((Get-Location).Path)\backend,target=/app" `
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
- [Histórico de mudanças](CHANGELOG.md)

O RFC acadêmico permanece como a especificação principal do projeto. Os documentos deste repositório registram o que já foi implementado e as limitações conhecidas da PoC.
