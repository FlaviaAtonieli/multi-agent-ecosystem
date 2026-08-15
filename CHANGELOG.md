# Histórico de Mudanças

Este arquivo registra alterações relevantes da PoC. As datas correspondem ao material disponível no projeto e não substituem tags ou releases do GitHub.

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
