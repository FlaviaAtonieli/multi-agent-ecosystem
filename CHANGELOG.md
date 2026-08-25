# Histórico de Mudanças

Este arquivo registra alterações relevantes da PoC. As datas correspondem ao material disponível no projeto e não substituem tags ou releases do GitHub.

## 2026-08-25 - Perfil REVIEWER e revisão humana de solicitações

### Adicionado

- perfil `REVIEWER` (`app/core/roles.py`, `HUMAN_REVIEW_ROLES`);
- endpoint `POST /api/v1/requests/{id}/review` (decisão `approve`/`reject` com observações), restrito a `REVIEWER` ou `ADMIN`, não restrito ao dono da solicitação;
- status `REJECTED` para solicitações rejeitadas na revisão humana;
- eventos `HUMAN_REVIEW_APPROVED` / `HUMAN_REVIEW_REJECTED` na timeline de rastreabilidade;
- 5 testes cobrindo aprovação, rejeição, controle de acesso por papel, tentativa fora do status `VALIDATING` e revisão de solicitação de outro usuário.

### Contexto

- o perfil `REVIEWER` não está definido na RFC (a especificação principal do projeto); vem de `docs/Documento_de_referencia.md`, um documento à parte com escopo mais amplo (Agentic Control Plane). Implementado mesmo assim por decisão explícita, fora do escopo formal da RFC v3.1;
- fecha a lacuna de "revisão humana" citada em `docs/integrations/model-provider.md` e no princípio de humano no loop (RFC, Seção 6).

## 2026-08-25 - Agent Skills de Regras de Negócio e Arquitetura

### Adicionado

- executor real e servidor MCP para a Agent Skill de Regras de Negócio (`app/agent_catalog/mcp_servers/business_rules_server.py`);
- executor real e servidor MCP para a Agent Skill de Arquitetura de Software (`app/agent_catalog/mcp_servers/architecture_server.py`);
- manifestos de exemplo `business-rules-skill.md` e `architecture-skill.md`;
- teste de orquestração multiagente acionando as três Agent Skills (Código Legado, Regras de Negócio, Arquitetura) numa mesma análise, comprovando o critério mínimo de sucesso da PoC (RFC 5.5: ao menos três Agent Skills numa mesma análise).

### Não incluído

- seleção dinâmica de skills (roteamento continua por correspondência exata de domínio, decisão deliberada de escopo);
- perfil `REVIEWER`.

## 2026-08-25 - Fechamento do Marco M5 (Modelagem Técnica da PoC)

### Adicionado

- RFC (v3.1): Marco M5 marcado como concluído no roadmap (Tabela 11).

### Contexto

- stack tecnológica, modelo de dados, contrato do agente (modelo.md) e estratégia de implementação já estavam definidos na Seção 5 da RFC e refletidos na implementação (base, orientação, orquestração, RAG, provedores LLM, catálogo de Agent Skills e Quality Gate);
- este marco formaliza o fechamento documental, sem mudança de escopo técnico.

## 2026-07-31 - Fundação de provedores de modelo

### Adicionado

- interface interna para provedores;
- provedor `mock`;
- adaptador da OpenAI;
- configuração desabilitada por padrão;
- perfil `TECHNICIAN`;
- endpoint administrativo de alteração de perfil;
- migration `0003_llm_foundation`;
- tabela `llm_invocations`;
- `LLM Call ID` vinculado ao `Trace ID`;
- hashes de entrada e saída;
- registro de tokens e latência;
- sanitização de padrões sensíveis;
- endpoints de status, planejamento e consulta de rastros;
- aprovação humana obrigatória;
- testes do fluxo com provedor simulado.

### Não incluído

- chave de produção;
- execução automática de Agent Skills;
- publicação automática;
- armazenamento integral de prompts por padrão;
- tela administrativa para editar segredos;
- gerenciador de segredos de produção.

## 2026-07-30 - Fundação de orquestração

### Adicionado

- solicitação técnica;
- geração de `Trace ID`;
- estados `AWAITING_CONTEXT` e `QUALIFIED`;
- complementação de contexto;
- execução inicial de orquestração;
- timeline de eventos;
- histórico de solicitações;
- métricas do dashboard baseadas no banco;
- migration `0002_orchestration_foundation`;
- testes do fluxo inicial.

### Limitações

- sem seleção dinâmica de Agent Skills;
- sem execução multiagente;
- sem consolidação de respostas parciais;
- sem Quality Gate final.

## 2026-07-22 - Base da aplicação

### Adicionado

- monorepo com frontend e backend;
- Docker Compose;
- React, TypeScript e Vite;
- FastAPI, SQLAlchemy e Alembic;
- PostgreSQL;
- cadastro e login;
- sessão opaca;
- proteção CSRF;
- rate limiting;
- auditoria inicial;
- perfis `USER` e `ADMIN`;
- migrations de autenticação;
- testes iniciais do backend.
