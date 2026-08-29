# Histórico de Mudanças

Este arquivo registra alterações relevantes da PoC. As datas correspondem ao material disponível no projeto e não substituem tags ou releases do GitHub.

## 2026-08-26 - Redesign do frontend, fase 1: sistema de design e layout compartilhado

### Adicionado

- `docs/design/AgentHub-Especificacoes.md`: especificacao completa do redesign de frontend, salva como referencia para as proximas fases.
- Fontes Google (Manrope para titulos/numeros, IBM Plex Sans para corpo de texto) carregadas em `frontend/index.html`.
- Novo sistema de tokens de cor em `global.css` (`--bg-app`, `--bg-sidebar`, `--bg-card`, `--bg-input`, `--border-subtle`, `--border-strong`, `--text-primary/secondary/tertiary/muted`, acentos violeta/ciano/ambar/verde/vermelho) e keyframes de animacao reutilizaveis (`fade-up`, `pulse-dot-amber`, `pulse-dot-green`, `pop-in`).
- Agrupamento de navegacao no `AppShell` em duas secoes rotuladas ("PRINCIPAL": Visao geral, Nova solicitacao, Orquestracoes; "ECOSSISTEMA": Agent Skills, Auditoria) -- antes "Agent Skills" ficava fora do grupo Ecossistema mesmo sendo conceitualmente parte dele.

### Alterado

- `workspace.css` migrado para consumir os novos tokens em vez de cores hexadecimais fixas; topbar reduzida de 72px para 64px e padding do conteudo ajustado para `28px 32px 40px`, conforme a especificacao.

### Corrigido

- CSP do frontend (`nginx.conf`): `style-src`/`font-src` nao autorizavam `fonts.googleapis.com`/`fonts.gstatic.com`, entao as fontes do Google adicionadas nesta fase eram bloqueadas silenciosamente no ambiente real (nao aparecia no screenshot isolado, so no console do navegador) -- detectado ao inspecionar o console via Playwright durante a fase 2.

### Contexto

- primeira de 7 fases confirmadas para adequar o frontend a especificacao fornecida (`AgentHub-Especificacoes.md`), adaptando o conteudo fictício do documento (ex.: tabelas de exemplo em Agent Skills/Auditoria) para os dados reais do backend nas fases seguintes;
- fase 1 e a base de que as demais fases dependem (tokens, fontes, layout compartilhado) -- verificada com `npx tsc -b` e checagem visual via Playwright contra o ambiente Docker real.

## 2026-08-26 - Fecha a rodada de KPIs do M7 (Reducao do Tempo de Analise)

### Adicionado

- Pesquisa de benchmarks publicados sobre tempo de desenvolvedor gasto entendendo codigo legado (Sourcegraph, IN-COM Data Systems, Devox Software: 58-70% do tempo em compreensao de codigo) como contexto para o KPI "Reducao do Tempo de Analise" (RFC 1.6, meta >=30%).

### Contexto

- os benchmarks encontrados descrevem proporcao de tempo de trabalho, nao duracao absoluta de uma tarefa pontual -- nao sao comparaveis aos ~12-14s de resposta medidos da PoC sem uma conta invalida (maca com laranja);
- KPI registrado como "nao mensuravel nesta fase" em vez de forcar um numero: a medicao correta exige um estudo controlado (mesma tarefa, cronometrada com e sem a ferramenta), que e trabalho de campo, nao decidivel por pesquisa bibliografica;
- com isso, a primeira rodada de medicao dos 7 KPIs da RFC (Tabela 1) esta completa: 3 atingidos (Rastreabilidade, Articulacao entre Dominios, Extensibilidade), 1 nao atingido (Tempo Medio de Resposta), 1 ambiguo por definicao da RFC (Taxa de Sucesso End-to-End), 2 nao mensuraveis nesta fase (Qualidade do Manifesto por ambiguidade de metodologia, Reducao do Tempo de Analise por falta de linha de base).

## 2026-08-26 - Medicao de Qualidade do Manifesto (M7)

### Adicionado

- Medicao do KPI "Qualidade do Manifesto" em `docs/validation/evidence/2026-08-m7-kpi-measurement.md`: lote de 10 manifestos (4 fixtures validos + 6 variacoes com defeitos realistas de autoria) contra `POST /agent-skills/import` real.

### Contexto

- resultado bruto (4/10 = 40% validos) e enganoso e nao deve ser lido como "40%": o lote foi montado propositalmente com 60% de defeitos para testar cobertura do validador, nao para simular submissoes organicas reais;
- leitura correta: **10/10 classificacoes corretas** do validador (4 validos aceitos, 6 defeitos rejeitados com mensagem especifica e acionavel cada);
- a RFC nao define se a meta de "80% validos" mede precisao do validador (medido: 100%) ou taxa de submissoes organicas de usuarios reais (nao medivel sem dados de uso real);
- Reducao do Tempo de Analise (meta >=30%) continua bloqueada: nao existe linha de base de tempo manual em nenhum lugar do projeto -- precisa de estimativa ou entrevista, nao e medivel so com codigo.

## 2026-08-26 - Fundamentacao teorica e recorte de contexto por agente

### Adicionado

- RFC (v3.3): paragrafos novos na Secao 3.1 contrastando agente generico vs. agente especialista (ancorado no proprio Benchmark da Secao 1.3 -- AutoGPT como exemplo de agente generico); taxonomia agente de negocio/processo/ferramenta/orquestrador mapeada explicitamente sobre os componentes do Quadro 3 (Secao 3.2);
- recorte de contexto por agente (RFC 6.1 "Protecao de Contexto"): cada Agent Skill agora recebe um prompt e uma consulta RAG explicitamente escopados ao seu proprio dominio (`LLMPlanRequest.analysis_domain_label`, `app/llm/prompts.py`, `app/rag/service.py`) -- antes, os 4 executores enviavam o mesmo prompt generico ao LLM independente do dominio;
- feedback visual de sucesso no frontend (`alert-success`): a tela de Orquestracao agora confirma explicitamente quando o contexto e complementado ou a orquestracao e executada, nao so por mudanca de status.

### Contexto

- decorre de uma auditoria pedida pela autora contra um checklist de 10 categorias (fundamentacao teorica, arquitetura, modelagem de agentes, orquestracao, contratos, PoC, frontend, seguranca, observabilidade, escrita academica) -- 5 lacunas reais encontradas e fechadas nesta entrada;
- 2 novos testes (`test_llm_prompts.py`) cobrindo o recorte de contexto, sem custo de chamada real.

## 2026-08-26 - Primeira medicao de KPIs (M7) e correcao de schema

### Corrigido

- `agent_skills.input_contract_ref`/`output_contract_ref` ampliados de `VARCHAR(200)` para `VARCHAR(500)` (migration `0007_widen_contract_refs`). Bug real: todos os 4 manifestos de fixture tem 205 caracteres no `output_contract_ref`, excedendo o limite antigo -- nunca detectado porque a suite de testes roda em SQLite, que nao aplica limite de tamanho de coluna.

### Adicionado

- Primeira rodada de medicao dos KPIs da RFC (Secao 1.6) contra PostgreSQL real via docker compose, sem provedor mock: `docs/validation/evidence/2026-08-m7-kpi-measurement.md`.

### Contexto

- Rastreabilidade (100%), Articulacao entre Dominios (3 agentes) e Extensibilidade (1 skill) atingidos;
- Tempo Medio de Resposta (meta <=10s) nao atingido: medido 11,8s medio / 13,9s com overhead de orquestracao, usando o modelo gratuito padrao;
- Taxa de Sucesso End-to-End ambigua -- a RFC nao define se "sucesso" exige aprovacao do Quality Gate sem revisao humana ou so a execucao tecnica sem falha; ver o documento de evidencia para os dois calculos;
- Qualidade do Manifesto e Reducao do Tempo de Analise ainda sem metodologia de medicao definida;
- medicao feita contra as branches ainda nao mergeadas em main -- deve ser repetida apos o merge.

## 2026-08-26 - Remocao do provedor mock

### Removido

- `MockLLMProvider` e `MockEmbeddingProvider`, junto com o valor `mock` de `LLM_PROVIDER`;
- fallback silencioso para embedding mock em `rag/factory.py` quando a OpenRouter nao esta configurada -- agora levanta `RAGConfigurationError` explicitamente.

### Adicionado

- `app/core/retry.py` (`retry_on_transient_error`): retry generico de ate 2 tentativas, aplicado em `OpenRouterLLMProvider.generate_plan` e `OpenRouterEmbeddingProvider.embed`, cobrindo rate limit (429), erro de conexao/timeout e resposta JSON incompleta (modelo gratuito ignorando o `response_format` estrito).

### Alterado

- `LLM_PROVIDER` passa a ser `openrouter` por padrao (antes `mock`); `LLM_MODEL`/`LLM_ALLOWED_MODELS` passam a apontar para `nvidia/nemotron-3-super-120b-a12b:free`, validado empiricamente para honrar o `response_format` estrito da aplicacao;
- suite de testes do backend reescrita para chamar a OpenRouter de verdade (chat completions e embeddings), sem nenhuma chamada simulada; asserções que dependiam de conteudo exato do provedor mock foram generalizadas para tolerar variacao de saida de um modelo real;
- README e `docs/integrations/model-provider.md` atualizados: nao ha mais como rodar a aplicacao com integracao de modelo habilitada, nem a suite de testes, sem uma `OPENROUTER_API_KEY` real.

### Contexto

- decisao explicita da autora: o projeto passa a validar a integracao real com a OpenRouter desde o desenvolvimento, em vez de manter uma camada de simulacao;
- o modelo `openrouter/free` (roteador automatico de modelos gratuitos) foi testado e descartado como padrao: escolheu um modelo sem suporte a `structured_outputs` numa das chamadas, retornando JSON incompleto;
- flakiness real observada: duas rodadas completas da suite sem retry produziram 1-2 falhas cada (sempre passando isoladamente), atribuida a instabilidade do modelo gratuito compartilhado sob rajada de chamadas; apos o retry, uma rodada completa passou 33/33 sem falhas;
- risco conhecido: o modelo gratuito padrao tem limite de 50 requisicoes/dia sem creditos comprados; ver `docs/integrations/model-provider.md`.

## 2026-08-25 - Fechamento do Marco M6 (Implementacao da PoC)

### Adicionado

- RFC (v3.2): Marco M6 marcado como concluido no roadmap (Tabela 11);
- nota de status na secao 5.5 confirmando os 7 criterios minimos de sucesso implementados e testados.

### Contexto

- fecha o marco de implementacao da PoC (protocolo funcional, APIs principais, banco de dados, fluxo plug-and-play executavel), cujo conteudo ja estava coberto pelo trabalho registrado nas entradas anteriores deste changelog (Agent Skills, revisao humana, resposta consolidada, extensibilidade);
- a medicao formal dos KPIs da RFC (secao 5.5) fica para o M7 (Validacao e Avaliacao), prazo ate 30/10/2026.

## 2026-08-25 - Extensibilidade plug-and-play (RFC 5.5 criterio 7)

### Adicionado

- quarta Agent Skill, Segurança da Informação (`seguranca_informacao`), com executor e servidor MCP proprios (`SecuritySkillExecutor`, `security_server.py`);
- teste `test_new_agent_skill_couples_without_orchestrator_changes` provando que a nova skill e reconhecida e acionada pelo Orquestrador sem qualquer mudanca em `agent_skill_orchestration_service.py`, `orchestration_service.py`, `quality_gate/service.py` ou `registry.py` (confirmado por `git diff --stat` vazio nesses arquivos);
- evidencia formal em `docs/validation/evidence/2026-08-plug-and-play-extensibility.md`.

### Contexto

- fecha o ultimo criterio minimo de sucesso pendente da RFC 5.5 e a etapa 7 da estrategia de implementacao (RFC 5.4);
- os unicos dois pontos tocados foram o tipo `DomainLiteral` (camada de contratos) e uma linha em `mcp_client._DOMAIN_SERVER_MODULES` (registro do plugin) -- nenhum dos dois e o "nucleo do Orquestrador" que RF05 protege.

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
