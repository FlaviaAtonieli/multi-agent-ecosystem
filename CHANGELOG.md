# Histórico de Mudanças

Este arquivo registra alterações relevantes da PoC. As datas correspondem ao material disponível no projeto e não substituem tags ou releases do GitHub.

## 2026-08-30 - Corrige falha sistematica do openai/gpt-5-mini (schema JSON em modo strict)

### Corrigido

- `app/llm/schemas.py` (`strict_json_schema`, novo): o schema JSON enviado com `strict: true` nao listava em `required` os campos de `LLMPlan` com valor padrao no Pydantic (`required_agents`, `required_skills`, `risks`, `missing_information`, `requires_human_approval`) -- o modo estrito da OpenAI exige que todo campo de `properties` apareca em `required`. Um modelo `:free` do OpenRouter tolerava o schema malformado; `openai/gpt-5-mini`, roteado direto pra infraestrutura da OpenAI/Azure, rejeitava a chamada inteira com HTTP 400 antes de qualquer geracao -- 100% das chamadas falhavam. Usado agora pelos dois provedores (`openrouter_provider.py`, `openai_provider.py`).
- `app/core/config.py`: `LLM_MAX_OUTPUT_TOKENS` sobe de 1200 para 3000 -- modelos de raciocinio (como `gpt-5-mini`) gastam parte do teto em tokens de "pensamento" interno antes do conteudo visivel; 1200 ja era apertado mesmo com o schema corrigido.

### Adicionado

- `app/llm/base.py` (`LLMEmptyResponseError`): erro especifico para quando o provedor esgota o orcamento de saida so com raciocinio (`finish_reason=length`, conteudo vazio) -- nao entra no retry automatico (a mesma chamada falharia de novo do mesmo jeito), e gera uma mensagem especifica no evento de auditoria (`error_code=EMPTY_RESPONSE_TOKEN_BUDGET`) em vez do generico "falha no planejamento".

### Contexto

- a autora testou manualmente uma orquestracao com o modelo `openai/gpt-5-mini` e recebeu "Confianca geral: Baixa" com 0 respostas de Agent Skill consolidadas, pediu pra investigar a causa raiz antes de decidir o que fazer;
- investigacao real, sem chute: consultado `llm_invocations` direto no Postgres pra achar o trace/modelo exato, depois reproduzida a chamada exata fora do app (schema e prompt reais) pra capturar o erro completo -- a primeira hipotese (so estouro de orcamento de raciocinio) nao explicava o padrao 100% consistente; a reproducao revelou o HTTP 400 real da OpenAI, causa raiz mais fundamental;
- decisao confirmada com a autora: corrigir o schema, subir o teto de tokens, e melhorar a mensagem de erro -- as tres coisas, nao so uma;
- verificado com `ruff`/`mypy app` (limpos), suite completa do backend (real, sem mock), e 2 execucoes reais consecutivas de `openai/gpt-5-mini` contra o prompt e schema exatos de producao, ambas com sucesso apos a correcao.

## 2026-08-30 - Animacao de "pensamento" durante a execucao da orquestracao

### Adicionado

- `frontend/src/components/orchestration/OrchestrationThinkingAnimation.tsx`: substitui o botao "Executando..." estatico por uma sequencia animada de etapas (selecao de Agent Skills, recuperacao RAG, uma etapa por dominio realmente consultado, avaliacao do Quality Gate, consolidacao), com uma linha citando o Trace ID e reforcando que cada etapa fica registrada na Auditoria.
- `frontend/src/pages/OrchestrationPage.tsx`: busca o catalogo de Agent Skills ativas (`agentSkillsApi.listSkills(true)`) para nomear os dominios reais na animacao quando `requested_domains` chega vazio da tela de criacao (caso em que o Orquestrador consulta todas as skills ativas -- `_resolve_target_skills` no backend).
- `frontend/src/api/orchestrationApi.ts`: tipo `TechnicalRequest` ganha `requested_domains` (o backend ja expunha o campo; faltava no tipo do frontend).

### Contexto

- pedido direto da autora ao notar, durante um teste manual guiado, que o estado "Executando..." sem nenhum feedback visual durante ~1-2 minutos (4 chamadas reais de LLM) passava ansiedade;
- decisao de design: a animacao e deliberadamente "fake" (nao reflete o passo exato do backend em tempo real, ja que o `execute` e uma unica chamada sincrona sem streaming/SSE hoje), mas so nomeia etapas e dominios reais do pipeline desta solicitacao especifica, nunca conteudo decorativo desconectado do que de fato acontece;
- verificado com `tsc -b` (limpo) e Playwright contra o stack real: solicitacao criada, execucao disparada, animacao progredindo pelos 4 dominios reais, e o resultado final (4 cards de skill, sintese consolidada, timeline) renderizando corretamente ao final.

## 2026-08-30 - Validacao de qualidade do RAG

### Adicionado

- `backend/app/rag/evaluation.py`: metricas de recuperacao de informacao (Precision@k, Recall@k, Reciprocal Rank) e um gabarito de 8 perguntas com artefatos relevantes esperados, definido manualmente a partir do conteudo real do fixture `legacy_billing` (nao gerado automaticamente).
- `backend/tests/test_rag_quality.py`: `test_retrieval_quality_against_ground_truth` mede a recuperacao real (embeddings da OpenRouter, sem mock) contra o gabarito e trava a suite se MRR ou Recall@3 medios cairem abaixo de limiares fixados com margem real sobre o medido (MRR 0.875, Recall@3 0.812); `test_rag_enabled_plan_reflects_retrieved_context` prova mecanicamente (evento `RAG_RETRIEVAL_COMPLETED` + chunks recuperados) que o contexto recuperado alimentou a chamada, sem travar a suite numa asercao fragil sobre o texto livre do modelo gratuito.
- `docs/validation/evidence/2026-08-30-rag-quality-validation.md`: registra os numeros medidos, incluindo a unica pergunta que falhou (P@3=R@3=0.00, sobre uma tabela que nao existe no schema) sem esconder o resultado, e tres respostas reais capturadas comparando com/sem RAG habilitado para a mesma pergunta.

### Contexto

- pedido direto da autora depois de validar a rubrica oficial da linha "IA" do Portfolio Directions do professor, que lista como tema explicitamente vedado "solucoes que apenas consomem uma API de LLM por prompt, sem incorporar IA de fato" -- risco que ja estava registrado como pendencia de alta prioridade em `docs/gestao/agenthub-epicos-historias.csv` antes mesmo de ver a rubrica;
- decisao de escopo tomada durante a implementacao, nao perguntada antes: a comparacao com/sem RAG foi desenhada para nao depender de correspondencia literal de termos no texto livre do modelo (a primeira tentativa quebrou por causa da variacao natural do modelo gratuito -- documentada no proprio arquivo de evidencia), preferindo uma asercao mecanica confiavel na suite automatizada e evidencia qualitativa no documento;
- cobre so o dominio `codigo_legado` (unico com base de conhecimento indexada hoje) -- limitacao registrada explicitamente, nao escondida;
- verificado com `ruff`/`mypy app` (limpos) e suite completa do backend (execucao real contra a OpenRouter).

## 2026-08-30 - Perguntas de acompanhamento: continuar a interacao na mesma cadeia de orquestracao

### Adicionado

- Novo modelo `FollowUpExchange` (migration `0009_follow_up_exchanges`): cada pergunta de acompanhamento apos a execucao inicial vira sua propria linha, preservando o historico completo -- ao contrario de `ConsolidatedResponse` (uma por solicitacao, a "resposta final" unica do RFC 5.3), uma solicitacao pode acumular N trocas.
- `POST /agent-skills/requests/{id}/ask`: registra uma pergunta de acompanhamento, continuando a mesma cadeia de orquestracao (mesmo `trace_id`). `target_domain=null` transmite para todos os dominios que participaram da execucao original; um dominio especifico direciona a pergunta so aquele Agent Skill. Toda rodada -- mesmo com um unico agente -- passa pelo mesmo Quality Gate (RF11) da execucao inicial, seguindo o padrao ja estabelecido.
- `GET /orchestrations/{trace_id}/follow-ups`: lista o historico de trocas, em ordem.
- `LLMPlanRequest`/`SkillToolCall` ganham `additional_question`, incorporado ao prompt do planejador tecnico quando presente.
- Frontend: `FollowUpForm` (pergunta + seletor "Perguntar para" com os dominios que participaram da analise) e `FollowUpExchangeCard` (reaproveita os mesmos componentes de sintese-por-dominio e card-de-skill da fase anterior) exibidos apos qualquer execucao concluida.
- 3 novos testes (`test_follow_up.py`): exige execucao previa, broadcast persistindo corretamente, e pergunta direcionada a um dominio especifico (alem do 409 quando nao ha skill para o dominio pedido).

### Contexto

- pedido direto da autora: "ter uma acao de continuar com a interacao... poder perguntar para um agente em especifico... se tiver respostas de mais de um agente tem que seguir nosso padrao";
- duas decisoes de escopo confirmadas explicitamente antes da implementacao: manter historico completo (nao sobrescrever a resposta anterior) e sempre passar pelo Quality Gate, mesmo com um unico agente respondendo;
- verificado com `ruff`/`mypy`/`pytest` (53/53 testes, suite limpa apos re-execucoes isoladas confirmarem que as falhas anteriores eram a instabilidade ja documentada do modelo gratuito, nao regressao) no backend, `npx tsc -b` no frontend, e fluxo real via Playwright: pergunta em broadcast (8 skills, ~2min) e pergunta direcionada a um dominio (2 skills) confirmadas na tabela `follow_up_exchanges` e renderizadas corretamente na tela, incluindo apos reload.

## 2026-08-29 - Organiza a resposta final: sintese por dominio, achados e blocos de codigo

### Adicionado

- `ExecutionResultPanel`: a "Sintese consolidada" agora e separada por dominio (badge + paragrafo), em vez de um unico bloco de texto corrido com tags `[dominio]` coladas. Cada card de Agent Skill passa a mostrar tambem as descobertas tecnicas (`descobertas_tecnicas`) e, quando existe `trecho_referenciado`, renderiza em bloco de codigo monoespacado.
- Novo endpoint `GET /orchestrations/{trace_id}/skill-results`: persiste e expoe o resultado estruturado (`SkillToolResult`) de cada Agent Skill executada. Antes desta mudanca, `AgentSkillInvocation.result_payload` nunca era preenchido -- os dados detalhados por skill so existiam durante a resposta HTTP da execucao e se perdiam ao recarregar a pagina.
- Tela de Orquestracao passa a reaproveitar o `ExecutionResultPanel` tambem no caminho de reload (sem execucao fresca em memoria), buscando os resultados persistidos -- antes mostrava so o texto cru da sintese.
- Novo teste (`test_agent_skills.py`) cobrindo a persistencia e o novo endpoint.

### Corrigido

- Import circular real introduzido ao referenciar `SkillToolResult` em `app/schemas/orchestration.py`: os contratos de dados puros (`SkillToolResult`, `SkillToolCall`, etc.) foram extraidos de `tool_interface.py` para um novo modulo `app/agent_catalog/contracts.py`, sem depender de `app.services.llm_service` -- `tool_interface.py` (que tem os `SkillExecutor`, esses sim dependentes do LLM) passa a reexportar dali, mantendo todos os imports existentes no resto do projeto inalterados.

### Contexto

- pedido direto da autora ao ver a sintese consolidada renderizada como texto cru com tags `[dominio]` coladas (ex.: "[arquitetura_software] Plano tecnico... [regras_negocio] Plano tecnico...");
- verificado com `ruff`/`mypy`/`pytest` (51/51 testes, suite limpa) no backend, `npx tsc -b` no frontend, e fluxo real via Playwright: execucao completa com 8 Agent Skills (4 dominios, skills duplicadas de testes anteriores), sintese exibida separada por dominio tanto na execucao fresca quanto apos reload da pagina.

## 2026-08-29 - Coluna de uso de tokens na pagina de admin

### Adicionado

- `GET/PATCH /admin/users*` agora retornam `AdminUserRead` (estende `UserRead` com `tokens_used_today` e `daily_token_limit_per_user`) -- uma unica query agregada por usuario, nao N+1.
- Pagina `/admin`: nova coluna "Tokens hoje" com pill colorida (neutro/ambar >=70%/vermelho na cota) por usuario; contas ADMIN mostram "Isento".
- 5 novos testes (`test_admin.py`): gate de acesso (403 para nao-admin), listagem com uso agregado correto, troca de papel/status refletindo `AdminUserRead`, protecao contra autodegradacao do proprio admin.

### Contexto

- pedido direto da autora apos ver a cota de tokens funcionando: queria ver o consumo de cada usuario direto no painel de admin, sem precisar consultar o banco;
- endpoint `/admin/users` nao tinha nenhum teste ate agora -- fechado junto com esta mudanca, ja que o arquivo foi mexido de qualquer forma;
- verificado com `ruff`/`mypy`/`pytest` (50/50 testes, suite limpa) no backend, `npx tsc -b` no frontend, e fluxo real via Playwright logado como o admin de bootstrap.

## 2026-08-29 - Documenta a diferenca entre papel e cota de tokens

### Adicionado

- README (`## Fluxo disponível`): nova secao "Acesso e cota de uso" explicando as duas camadas independentes que controlam a execucao -- papel do usuario (TECHNICIAN/ADMIN, promovido via `/admin`) decide *se* alguem pode executar; a cota diaria de tokens decide *quanto* uma pessoa ja autorizada pode executar naquele dia. Deixa explicito que ter cota disponivel nao substitui o papel.

### Contexto

- motivado por uma pergunta real que misturou os dois conceitos ("Pedro nao precisa de acesso porque tem cota de tokens?") -- registrado para nao se repetir: sao verificacoes sequenciais e independentes, a cota so e avaliada depois que o papel ja passou.

## 2026-08-29 - Medidor visual de uso de tokens (TokenUsageMeter)

### Adicionado

- `TokenUsageMeter`: substitui o texto simples "Uso de tokens hoje: X / Y" por um card com barra de progresso, percentual em destaque e 3 estados de cor (violeta/ciano normal, ambar >=70%, vermelho ao atingir a cota) -- consistente com o design system do redesign de 7 fases (fonte Manrope nos numeros, tokens de cor existentes).

### Contexto

- feedback direto da autora: o indicador anterior era so texto pequeno cinza, sem o acabamento visual do resto do app;
- verificado com `npx tsc -b` e fluxo real via Playwright nos dois estados (uso baixo/normal e cota esgotada, este ultimo simulado com uma invocacao semeada direto no banco).

## 2026-08-29 - Confirma o limite de tokens/dia contra o preco real do modelo pago

### Contexto

- a autora perguntou de onde veio o numero 150000 -- documentado em `docs/integrations/model-provider.md`: e uma conta a partir dos tetos ja configurados (`LLM_MAX_INPUT_CHARS`/`LLM_MAX_OUTPUT_TOKENS`), nao uma calibracao de custo real;
- verificado contra o preco real do unico modelo pago da allowlist (`openai/gpt-5-mini`: $0,25/milhao tokens de entrada, $2,00/milhao de saida, fonte OpenRouter) -- no pior caso, 150000 tokens/dia custam ~US$0,30/dia por usuario; com US$10 de credito na conta, dura mais de 30 dias mesmo com varios usuarios testando;
- decisao explicita da autora: manter o valor como esta, ja que a margem e confortavel.

## 2026-08-29 - Cota diaria de tokens por usuario

### Adicionado

- `generate_technical_plan` (`app/services/llm_service.py`) agora verifica, antes de qualquer chamada ao provedor, a soma de `input_tokens + output_tokens` das invocacoes `COMPLETED` do usuario no dia corrente (UTC). Acima de `LLM_DAILY_TOKEN_LIMIT_PER_USER` (padrao 150000, `0` desabilita), a chamada e recusada com `429` antes de gastar creditos -- cobre os dois pontos de entrada que acionam o LLM (`POST /llm/requests/{id}/plan` e `POST /agent-skills/requests/{id}/execute`, ja que cada Agent Skill invocada chama a mesma funcao internamente). Contas `ADMIN` sao isentas.
- `GET /llm/status` expoe `daily_token_limit_per_user` e `tokens_used_today`; a tela de Orquestracao mostra "Uso de tokens hoje: X / Y" perto do botao de executar e desabilita o botao preventivamente quando a cota ja foi atingida.
- 2 novos testes (`test_llm.py`): bloqueio ao atingir a cota (sem custo de chamada real -- a checagem ocorre antes do provedor) e isencao de conta ADMIN (com uma chamada real, para confirmar que o fluxo completa).

### Contexto

- motivado por uma pergunta direta da autora sobre como proteger a assinatura da OpenRouter de um unico usuario consumir todos os creditos -- decisao explicita: cota simples por contagem de tokens, sem modelo de negocio free/pro por enquanto;
- verificado com `ruff`/`mypy`/`pytest` no backend (2 rodadas completas da suite, 1 flake isolado e nao relacionado em cada rodada -- mesmo padrao de instabilidade do modelo gratuito ja documentado em `docs/integrations/model-provider.md`, confirmado por re-execucao isolada), `npx tsc -b` no frontend, e fluxo real via Playwright: indicador "0 / 150.000" com uso normal, e estado bloqueado/vermelho com botao desabilitado apos simular uso acima da cota.

## 2026-08-29 - Pagina de administracao de usuarios

### Adicionado

- Pagina `/admin` (`AdminPage.tsx`): lista todos os usuarios registrados, com dropdown para trocar o papel (USER/TECHNICIAN/REVIEWER/ADMIN) e botao para ativar/desativar a conta -- reaproveita os endpoints `GET/PATCH /admin/users` que ja existiam no backend mas nao tinham nenhuma tela consumindo.
- Item de navegacao "Usuarios" numa nova secao "ADMINISTRACAO", visivel apenas para ADMIN.

### Contexto

- antes desta pagina, promover um usuario para TECHNICIAN (necessario para executar orquestracoes -- gate intencional de "Autorizacao por Perfil" da RFC) exigia chamar a API manualmente (curl/Postman) ou mexer direto no banco;
- motivado por um teste real do Pedro (revisor do repositorio) que ficou bloqueado no botao "Executar orquestracao" por nao ter papel tecnico;
- verificado com `npx tsc -b` e fluxo real via Playwright: login como o admin de bootstrap (`admin@agenthub.com`), promocao de um usuario de teste para TECHNICIAN pela UI, confirmado que o novo papel aparece imediatamente no topo da tela apos o usuario logar novamente;
- a senha do admin de bootstrap no ambiente Docker local estava dessincronizada do valor atual do `.env` (a conta foi criada em 31/07 com uma senha antiga, e o bootstrap so roda uma vez) -- corrigida diretamente no Postgres local para bater com o `.env` atual, sem impacto em dado de producao (ambiente e so o Docker Compose local de desenvolvimento).

## 2026-08-28 - Redesign do frontend, fase 7: tour de primeiro acesso (fecha o redesign de 7 fases)

### Adicionado

- `users.onboarding_completed_at` (migration `0008_user_onboarding`): persiste no backend se o usuario ja concluiu (ou pulou) o tour, em vez de localStorage -- sobrevive entre dispositivos/navegadores, conforme a propria recomendacao da especificacao (§8, item em aberto 4).
- Novo endpoint `POST /api/v1/auth/onboarding/complete` (idempotente): marca o onboarding como concluido para o usuario autenticado. Exposto em `UserRead`/`/auth/me`, entao o frontend sabe se deve mostrar o tour assim que a sessao carrega.
- `OnboardingTour` (`frontend/src/components/onboarding/OnboardingTour.tsx`): overlay de spotlight com 4 passos (navegacao principal, botao Nova solicitacao, pendencias ou cards de estatistica, atividade recente), destacando o elemento real da tela via `data-tour` + `getBoundingClientRect`. Heuristica de posicionamento tenta direita, depois abaixo, depois acima, depois esquerda do alvo -- necessario porque a sidebar (alvo do passo 1) e alta e estreita, sem espaco acima/abaixo dentro da viewport.
- Link "Rever tour" na topbar (`/dashboard?tour=1`), reabrindo o tour manualmente sem exigir refazer o onboarding no backend.
- 2 novos testes (`test_auth.py`): fluxo completo (`onboarding_completed_at` nulo -> completo) e idempotencia do endpoint.

### Corrigido

- Heuristica inicial de posicionamento do tooltip (so acima/abaixo do alvo) colocava o card diretamente sobre a propria sidebar no passo 1, cobrindo os itens de navegacao que deveriam ficar visiveis -- corrigido antes de qualquer commit, achado durante a verificacao visual via Playwright.

### Contexto

- setima e ultima fase do redesign de frontend (`docs/design/AgentHub-Especificacoes.md`) -- as 7 fases confirmadas no inicio do trabalho estao completas: sistema de design, Dashboard, Orquestracoes, wizard de Nova Solicitacao, Agent Skills, Auditoria e este tour;
- verificado com `ruff`/`mypy`/`pytest` (43/43 testes) no backend, `npx tsc -b` no frontend, e fluxo real via Playwright: tour aparece automaticamente no primeiro acesso, avanca pelos 4 passos, persiste apos "Concluir" (nao reaparece em reload), reabre via "Rever tour", e "Pular tour" fecha imediatamente.

## 2026-08-28 - Redesign do frontend, fase 6: Auditoria

### Adicionado

- Novo endpoint `GET /api/v1/audit/events` (backend/app/api/v1/endpoints/audit.py): listagem paginada de `OrchestrationEvent` entre TODAS as solicitações (nao mais escopada por dono), com filtro por agente (`actor`), busca por titulo/Trace ID da solicitacao, janela de dias configuravel, e 4 contadores do dia atual (eventos, decisoes automatizadas, intervencoes manuais, alertas de conformidade). Gated por `require_reviewer` (papeis REVIEWER/ADMIN) -- reaproveita a dependencia ja usada pela revisao humana.
- Pagina Auditoria (`/auditoria`): 4 cards de indicadores, busca + chips de filtro por agente + dropdown de periodo, tabela completa (Evento/Origem/Solicitacao/Trace ID/Data), e exportacao CSV client-side dos eventos carregados.
- Item de navegacao "Auditoria" no `AppShell` agora e um link real para usuarios REVIEWER/ADMIN (antes era um botao permanentemente desabilitado); continua desabilitado para USER/TECHNICIAN, evitando expor um link que sempre retornaria 403.
- 4 novos testes (`backend/tests/test_audit.py`): gate de papel, listagem cross-user, filtro por agente, filtro por busca -- todos sem custo de chamada real de LLM.

### Contexto

- sexta de 7 fases do redesign de frontend; os 4 cards de estatistica sao escopados a "hoje" (por desenho, conforme o label do primeiro card na especificacao), enquanto a tabela usa uma janela configuravel (7/14/30/90 dias) -- as duas janelas sao intencionalmente independentes, entao os cards podem mostrar 0 mesmo com linhas visiveis na tabela quando nenhum evento novo ocorreu no dia corrente;
- "Alertas de conformidade" e definido como eventos reais de falha (`LLM_INVOCATION_FAILED`, `AGENT_SKILL_INVOCATION_FAILED`, `HUMAN_REVIEW_REJECTED`), nao um conceito inventado;
- verificado com `ruff`/`mypy`/`pytest` (41/41 testes passando) no backend, `npx tsc -b` no frontend, e fluxo real via Playwright: usuario promovido a REVIEWER via SQL direto no Postgres do ambiente Docker, visibilidade cross-user confirmada (eventos de sessoes de teste anteriores, de outros usuarios, aparecem na trilha), filtro por agente e busca testados em conjunto.

## 2026-08-26 - Redesign do frontend, fase 5: Agent Skills

### Adicionado

- Catalogo de Agent Skills reescrito como grid de cards (3 colunas), com icone abreviado colorido por dominio, badge de estado, objetivo truncado em 2 linhas, badge de dominio e versao no rodape; hover eleva o card e realca a borda.
- Busca por nome e chips de filtro por estado (Habilitadas/Pendentes/Desabilitadas) com contagem ao vivo.

### Contexto

- quinta de 7 fases do redesign de frontend; a especificacao inventava um conceito de "agente responsavel" (Orientador/Legado/Orquestrador/Negocio/Quality Gate) e um estado "Beta" que nao existem no modelo real -- adaptado para os campos reais do backend: `AgentSkill.domain` (4 dominios reais, ja usado como badge) e `AgentSkill.status`/`enabled` (o estado "Pendente de validacao" reflete `status == "pending_validation"`, nao um rotulo inventado);
- verificado com `npx tsc -b`, rebuild Docker e fluxo real via Playwright: grid renderizado com dados reais (8 skills), filtro por chip e busca testados.

## 2026-08-26 - Redesign do frontend, fase 4: wizard de Nova Solicitacao

### Adicionado

- Formulario de Nova Solicitacao reescrito como wizard guiado de 3 etapas (Identificacao -> Problema & objetivo -> Contexto & restricoes), com stepper visual, validacao por etapa e navegacao Voltar/Continuar preservando os dados ja preenchidos.
- Painel de orientacao lateral: checklist de contexto ao vivo (pendente/atual/concluido) e caixa de dica especifica por etapa.
- Chips de sugestao no campo Contexto tecnico (Modulos, Tecnologias, Dependencias, Comportamento esperado) e campo Restricoes convertido em input de tags removiveis.

### Corrigido

- Checklist "Restricoes informadas" aparecia marcado como concluido logo na etapa 1, porque o campo de restricoes vem pre-preenchido com um valor padrao ("Nao executar alteracoes automaticamente") herdado do formulario anterior -- os itens da etapa 3 agora so avaliam seu estado quando o usuario de fato chega nela.

### Contexto

- quarta de 7 fases do redesign de frontend; **Contexto tecnico continua opcional** (nao obrigatorio como sugere a especificacao) para preservar o comportamento real do backend: uma solicitacao sem contexto suficiente e roteada para "Aguardando contexto" em vez de bloquear o envio -- esse fluxo ja e demonstrado nas fases 2 e 3;
- campo "Tipo de solicitacao" da especificacao (chips Duvida tecnica/Bug/Nova funcionalidade/...) foi omitido: nao existe campo correspondente em `CreateTechnicalRequestInput` no backend, e adicionar um controle que nao persiste nada seria enganoso;
- verificado com `npx tsc -b`, rebuild Docker e fluxo real via Playwright cobrindo as 3 etapas, validacao bloqueando avanco com titulo vazio, chip de sugestao de contexto, tags de restricao, volta preservando dados, e envio final gerando Trace ID.

## 2026-08-26 - Redesign do frontend, fase 3: Orquestracoes (historico)

### Adicionado

- Chips de filtro por status com contagem ao vivo ("Todas", "Aguardando", "Em execucao", "Concluida", "Erro"), mapeando os 10 status reais (`RequestStatus`) para as 4 categorias da especificacao (ex.: `RECEIVED`/`QUALIFIED`/`PLANNING`/`RUNNING`/`VALIDATING` agrupados em "Em execucao").
- Busca por titulo/Trace ID e ordenacao (mais recentes/mais antigas) na tabela de historico.
- Tabela completa (5 colunas: Solicitacao, Status, Trace ID, Data, Acoes) com coluna Acoes dependente do status: "Completar contexto" (outline ambar) para `AWAITING_CONTEXT`, "Ver detalhes" para os demais.

### Contexto

- terceira de 7 fases do redesign de frontend; verificado com `npx tsc -b`, rebuild Docker e fluxo real via Playwright (3 solicitacoes com status distintos, filtro por chip, busca por texto) -- console do navegador conferido, sem novos erros alem do 403 pre-existente e esperado de `/llm/status` para usuarios sem papel tecnico.

## 2026-08-26 - Redesign do frontend, fase 2: Visao Geral (Dashboard)

### Adicionado

- Banner de acao condicional (`ActionBanner`): aparece somente quando ha solicitacoes "Aguardando contexto", aponta para a mais antiga pendente e leva direto para a tela de complementacao.
- Card "Como o ecossistema decide" (`EcosystemFlowCard`): mini-diagrama horizontal Orientador -> Orquestrador -> Quality Gate.
- Icones e destaque visual nos 4 cards de estatistica (`MetricCard`); o card "Aguardando contexto" ganha borda/fundo ambar quando ha pendencias.
- Toolbar de busca + filtro por status na tabela "Solicitacoes tecnicas" do dashboard.
- Dots de atividade coloridos por origem do evento (usuario, orientador de interacao, orquestrador, agentes) na coluna "Atividade recente".

### Corrigido

- CSP do frontend (`nginx.conf`) bloqueava o carregamento das fontes Google (Manrope/IBM Plex Sans) adicionadas na fase 1 -- `style-src`/`font-src` nao autorizavam `fonts.googleapis.com`/`fonts.gstatic.com`, entao as fontes nunca chegavam a carregar no ambiente real (only detectado ao inspecionar o console do navegador via Playwright, nao pelo screenshot visual isolado).

### Contexto

- segunda de 7 fases do redesign de frontend; adapta os elementos do dashboard aos dados reais (`/dashboard/summary`) em vez do conteudo de exemplo da especificacao;
- a falha de CSP reforca a necessidade de checar o console do navegador (nao so a captura visual) ao validar mudancas de frontend contra o ambiente Docker real.

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
