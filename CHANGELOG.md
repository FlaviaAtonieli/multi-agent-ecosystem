# Histórico de Mudanças

Este arquivo registra alterações relevantes da PoC. As datas correspondem ao material disponível no projeto e não substituem tags ou releases do GitHub.

## 2026-09-25 - Pagina de conta: editar nome, trocar senha, excluir conta

### Adicionado

- `PATCH /api/v1/auth/me` (editar nome), `POST /api/v1/auth/me/password` (trocar senha, exige a senha atual, recusada com 409 pra conta GitHub-only), `DELETE /api/v1/auth/me` (excluir a propria conta).
- `UserRead` ganha `has_password: bool` -- helper `_to_user_read()` centraliza o calculo (usado em todo endpoint de `auth.py` e em `admin.py`), pra nao repetir `user.password_hash is not None` em varios pontos e esquecer um.
- Nova pagina `/account`: perfil (nome editavel, e-mail read-only com indicacao de origem), seguranca (trocar senha, escondida se a conta for GitHub-only), papel (somente leitura), clas em que participa (lista + link pra `/clans`), zona de risco (excluir conta, com confirmacao por e-mail digitado). Avatar/nome no topbar (`AppShell.tsx`) vira link pra essa pagina.
- 7 testes novos em `test_account.py`: editar nome, `has_password=true` pra conta por senha, trocar senha com sucesso (login com a senha nova depois confirma), senha atual errada (401), conta GitHub-only recusa troca de senha (409), exclusao desativa e escuba a conta E revoga a sessao (confirma 401 em `/me` depois), exclusao preserva dado que o usuario criou (cla continua existindo).

### Corrigido

- **Achado ao implementar exclusao de conta**: o plano original previa bloquear a exclusao só quando o usuario fosse dono de uma Agent Skill com invocacao registrada (`AgentSkillInvocation.agent_skill_id`, `ondelete=RESTRICT`). Mapeando todas as FKs de `users.id` no banco, apareceram outras 4 colunas com a mesma trava `RESTRICT`: `AgentSkill.submitted_by_id`, `Clan.created_by_id`, `ClanMembership.added_by_id`, `FollowUpExchange.asked_by_id` -- e a mais decisiva, `LLMInvocation.user_id`, criada em toda orquestracao ja executada. Na pratica um `DELETE` de verdade falharia pra quase qualquer usuario que ja usou o sistema, nao so um caso de borda raro. Solucao (confirmada com a autora antes de implementar): exclusao vira **soft delete** -- desativa a conta e limpa nome/e-mail/avatar/github_id/senha, preservando a linha e todo o historico que aponta pra ela.

### Contexto

- a pedido da autora, ultimo item da leva de PRs combinada nesta sessao (A-F).
- decisao de soft-delete vs hard-delete-que-sempre-falha foi perguntada e confirmada antes de implementar, depois do mapeamento das FKs mudar o entendimento do problema.

## 2026-09-25 - Clas: grupos auto-servico, terceira visibilidade de Agent Skill

### Adicionado

- Migration `0013_clans`: tabelas `clans` e `clan_memberships` (M:N), coluna `agent_skills.clan_id` (`ondelete=SET NULL` -- uma skill sobrevive a apagar o cla, so fica orfa ate ser re-escopada).
- `app/services/clan_service.py`: `create_clan` (criador vira membro automaticamente), `add_member`/`remove_member` (so um membro atual do cla, ou ADMIN, pode gerenciar -- sem fluxo de convite/aceite nesta primeira versao), `list_user_clans`, `is_member`.
- `GET/POST /api/v1/clans`, `GET /api/v1/clans/{id}`, `POST /api/v1/clans/{id}/members` (por e-mail), `DELETE /api/v1/clans/{id}/members/{user_id}` -- todas exigem `get_current_user` (qualquer usuario autenticado, criacao de cla nao e restrita a ADMIN/TECHNICIAN).
- `agent_catalog/registry.py::_visibility_filter` ganha uma terceira condicao: skill `CLAN` visivel a quem e membro do `clan_id` dela. Mesma regra replicada no segundo ponto de checagem de visibilidade (`GET /agent-skills/{id}`, fora do registry).
- Formularios de criar/importar Agent Skill (`AgentSkillCreatePage.tsx`, `AgentSkillImportPage.tsx`) ganham selecao de visibilidade (Privada/Cla/Oficial) com seletor de cla (`clansApi.listMine()`), em vez de sempre mandar o padrao do backend sem escolha nenhuma.
- Nova pagina `ClansPage.tsx` (`/clans`, nav em "ECOSSISTEMA"): lista todos os clas, cria novo, abre detalhe com membros e adicionar/remover por e-mail.
- 8 testes novos em `test_clans.py`: criacao com auto-join, nome duplicado (409), membro adiciona/remove, nao-membro tenta adicionar (403), ADMIN gerencia sem ser membro, skill CLAN visivel so a membros (cenario completo com 3 contas), criar skill CLAN exige ser membro do cla alvo, `clan_id` obrigatorio quando `visibility=CLAN` (422).

### Corrigido

- Achado ao implementar: `AgentSkillCreatePage.tsx` dizia na propria tela "Ela nasce **privada**", mas a chamada `agentSkillsApi.createSkill(...)` nunca mandava `visibility` nenhum -- toda skill criada por esse formulario sempre virou `OFFICIAL` de verdade, nunca `PRIVATE` como o texto prometia. Corrigido junto com a adicao do seletor (agora o valor enviado é sempre explicito, nunca implicito).

### Contexto

- a pedido da autora: retomada de uma ideia mais antiga, ja prevista no enum de `visibility` desde a migration 0010 (`OFFICIAL/PRIVATE/CLAN/PUBLIC`), mas nunca implementada alem das duas primeiras. `PUBLIC` continua fora de escopo, sem uso definido.
- tres decisoes de escopo perguntadas e confirmadas antes de implementar: cla gate skill de Agent Skill (nao solicitacoes/historico); qualquer usuario cria e gerencia membros (nao so ADMIN); usuario pode estar em varios clas (M:N, nao 1:1).
- adicao de membro e direta, sem convite/aceite -- destacado como ponto de atencao pro review: e a leitura mais literal de "qualquer membro pode adicionar", mas significa que alguem pode ser colocado num cla sem consentimento previo.

## 2026-09-25 - Ranking de Agent Skills oficiais mais usadas

### Adicionado

- `GET /api/v1/agent-skills/ranking?limit=N`: agrega `agent_skill_invocations` por skill, restrito a `visibility == OFFICIAL` e `status == COMPLETED` -- skill privada nunca aparece (vazaria atividade de outro usuario) e invocacao que falhou nao conta como popularidade. `official_skill_usage_ranking()` em `registry.py`.
- `AgentSkillsPage.tsx`: secao "Mais usadas" acima da grade do catalogo, top 5, com medalha nas 3 primeiras posicoes e contagem de execucoes por skill. So aparece se houver pelo menos uma invocacao registrada (sem estado vazio decorativo).
- `test_skill_usage_ranking_counts_only_official_and_completed`: prova as tres regras de uma vez -- FAILED nao conta, skill PRIVATE com mais invocacoes que todas as outras juntas nunca aparece, ordenacao por contagem desc.

### Contexto

- a pedido da autora: contagem "todo o historico" (sem janela de tempo), so invocacoes bem-sucedidas, top 5 -- as tres decisoes de escopo foram perguntadas antes de implementar.
- rota `/ranking` registrada antes de `/{skill_id}` no router -- caminho estatico precisa vir antes do dinamico, senao o FastAPI tentaria resolver "ranking" como um `skill_id`.
- observado rodando a suite completa de `test_agent_skills.py` (nao investigado, pre-existente): 2 testes que fazem chamada real ao modelo gratuito falharam com `response.choices` vindo `None` da OpenRouter -- stack trace nao toca nenhum arquivo tocado nesta mudanca (é `openrouter_provider.py`/`llm_service.py`), mesma instabilidade do modelo `:free` ja documentada em outros pontos do projeto.

## 2026-09-25 - Auditoria volta a ser exclusiva de ADMIN

### Corrigido

- `audit.py`: `GET /api/v1/audit/events` trocou o gate de `get_current_user` (qualquer usuario autenticado, com escopo por dono pra quem nao fosse REVIEWER/ADMIN) para `require_admin` -- reverte a decisao de 2026-09-14 (ver entrada correspondente abaixo). A query e o `_count_today` deixam de aplicar qualquer filtro por dono, ja que agora so ADMIN chega la.
- `test_audit.py`: reescrito -- `test_audit_events_forbidden_for_plain_user` e `test_audit_events_forbidden_for_reviewer` (novo -- REVIEWER tinha acesso de sistema antes desta reversao, precisa confirmar que perdeu tambem) substituem os testes que assumiam acesso escopado; os demais passam a promover pra ADMIN em vez de REVIEWER.
- `AppShell.tsx`: link "Auditoria" sai de "ECOSSISTEMA" (visivel a todo mundo) e entra em "ADMINISTRACAO", junto com "Usuarios" -- atras do mesmo gate `user?.role === 'ADMIN'`.

### Contexto

- a pedido da autora: "vamos remover a pagina de auditoria dos usuarios e manter ela apenas para adm" -- reversao explicita da decisao anterior, nao uma correcao de bug.
- decisao de onde colocar o link ("Auditoria" dentro de "ADMINISTRACAO" vs. secao propria) perguntada e confirmada antes de implementar.

## 2026-09-25 - Corrige popover/widget fixo posicionado errado; botao de anexo estilizado

### Corrigido

- **Bug real encontrado em validacao visual**: o popover do `(!)` (`StatusBadge.tsx`) e o widget de "processando" (`OrchestrationThinkingAnimation.tsx`) apareciam deslocados/sobrepondo conteudo em vez de fixos no lugar certo. Causa: `position: fixed` so e relativo ao viewport se nenhum ancestral tiver `transform` -- e a classe `fade-up` (`global.css`), usada pra animar a entrada de quase todo painel da aplicacao, termina com `transform: translateY(0)` (fill-mode `both`), que continua sendo um `transform` "ativo" pros fins da spec de CSS mesmo em repouso. Qualquer ancestral com essa classe virava o container de posicionamento errado. Corrigido renderizando os dois via `createPortal(..., document.body)` -- escapam de qualquer ancestral, fixos de verdade ao viewport.
- `StatusBadge.tsx`: popover tambem ganhou clamping horizontal (nao passa mais da borda direita da tela).
- `NewRequestPage.tsx` (wizard, passo 3): o campo de anexo usava o `<input type="file">` nativo do navegador, com o visual padrao ("Escolher Arquivos"). Trocado pelo mesmo padrao ja usado em `AttachmentsSection.tsx` (label estilizada como `workspace-secondary-action` escondendo o input real) -- consistencia visual entre os dois pontos de anexo do app.

### Adicionado

- `OrchestrationThinkingAnimation.tsx`: o marcador do cabecalho do widget vira um "orbe" com nucleo brilhante (gradiente radial violeta/ciano) e dois aneis pulsando em atraso (`workspace-orb-ring`), a pedido da autora ("uma animacao mais bonita, tipo uma rede neural"). Mantem `prefers-reduced-motion` respeitado (aneis somem, nucleo fica estatico).

### Contexto

- a pedido da autora, apos validar visualmente os PRs #56/#57 rodando localmente e mandar capturas de tela mostrando os dois bugs de posicionamento e o pedido de estilo do botao/animacao.
- os dois bugs de posicionamento tem a mesma causa raiz -- vale ficar de olho em qualquer novo componente `position: fixed` daqui pra frente, sempre que puder aparecer dentro de um container `fade-up` (praticamente todo painel da aplicacao usa essa classe).

## 2026-09-21 - Animacao de processando vira widget fixo no canto da tela

### Corrigido

- `OrchestrationThinkingAnimation.tsx`: a animacao de passos (ja existia, so client-side, sem progresso real do backend) deixa de ficar embutida no meio do formulario de execucao -- agora renderiza como um card fixo no canto inferior direito (`position: fixed`), com cabecalho clicavel pra recolher/expandir. Recolhido, mostra so "Processando orquestracao" + o passo atual; expandido, mostra a lista completa de passos e o Trace ID, igual antes.
- Nenhuma mudanca em `OrchestrationPage.tsx` foi necessaria -- o componente ja era renderizado condicionalmente em `{executing && (...)}`; virar `position: fixed` foi suficiente pra tirar do fluxo da pagina, sem a pagina empurrar conteudo pra baixo enquanto a orquestracao roda.

### Contexto

- a pedido da autora: a espera da orquestracao ficava "sem status" visivel de forma incomoda -- queria a tela livre pra acompanhar o resto do conteudo da pagina enquanto um indicador fixo mostra que algo esta rodando.
- corpo do widget expandido ganhou `max-height`+scroll proprio (nao existia limite antes) -- pensado pra quando `domains` tiver varios itens e a lista de passos crescer.

## 2026-09-21 - Ajustes de UX: status da orquestracao, catalogo de skills, sidebar

### Corrigido

- `StatusBadge.tsx`: cada status de solicitacao (Aguardando contexto, Quality Gate, Em execucao, etc.) ganha um gatilho `(!)` ao lado, que abre um popover explicando o que aquele status significa -- antes o usuario via o rotulo sem contexto de "o que e isso e em que momento estou".
- `AgentSkillsPage.tsx`: rotulos "Habilitada"/"Desabilitada" (badge e filtro) viram "Disponivel"/"Indisponivel" -- o rotulo antigo parecia descrever uma acao do proprio usuario, mas habilitar/desabilitar sempre foi exclusivo de ADMIN (`canManage`). O botao de ADMIN passa a dizer "Disponibilizar no catalogo"/"Remover do catalogo" em vez de repetir o mesmo verbo do rotulo.
- `AppShell.tsx`: removido o bloco "Ecossistema operacional / Base de orquestracao v1" no rodape da sidebar -- nao carregava informacao nenhuma (texto estatico, nunca refletiu estado real).

### Contexto

- a pedido da autora, apos revisar a aplicacao rodando e listar uma serie de ajustes de UX espalhados por varias paginas -- este e o primeiro de uma leva de PRs pequenos e empilhados (plano registrado na sessao).
- popover de status usa `position: fixed` calculado via `getBoundingClientRect`, mesmo padrao ja usado pelo tooltip do onboarding tour (`OnboardingTour.tsx`) -- evita ser cortado pelo `overflow` das celulas de tabela onde `StatusBadge` tambem aparece (`OrchestrationsPage.tsx`, `RecentRequestsTable.tsx`).

## 2026-09-21 - RAG nos 4 dominios de Agent Skill; correcao de documentacao desatualizada

### Adicionado

- Base de conhecimento propria para os 3 dominios que so tinham executor real sem RAG: `backend/app/rag/fixtures/business_rules/` (`change-request-history.md`, `pricing-policy.md`), `backend/app/rag/fixtures/architecture/` (`module-dependency-map.md`, `deployment-topology.md`) e `backend/app/rag/fixtures/security/` (`access-control-notes.md`, `data-classification.md`) -- fixtures sinteticas, ancoradas no mesmo sistema legado fictício ja usado em `legacy_billing`, cada uma sob um angulo diferente (historico de decisao de negocio, acoplamento estrutural, controle de acesso/LGPD).
- `app/rag/evaluation.py`: `GROUND_TRUTH_BY_DOMAIN`, gabarito manual por dominio (5 perguntas novas por dominio, lidas diretamente do conteudo das fixtures). `backend/tests/test_rag_quality.py` generalizado pra co-indexar os 4 dominios na mesma base (cenario real de producao -- o retriever nao filtra por dominio) e medir Precision@3/Recall@3/MRR por dominio, com limiares de regressao proprios por dominio.
- `docs/validation/evidence/2026-09-rag-multi-domain-quality-validation.md`: resultado medido (MRR 0.875-1.000, Recall@3 0.750-1.000 conforme o dominio) com leitura honesta, incluindo a queda esperada de Recall@3 do dominio original (0.812 -> 0.750) por causa dos novos distratores.
- `app/db/seed_knowledge_base.py`: seed de producao passa a indexar as 4 pastas de fixture, nao so `legacy_billing`.

### Corrigido

- `docs/architecture/overview.md`: corrigidas duas afirmacoes desatualizadas -- dizia que so "Codigo Legado" tinha executor real (hoje sao 4 skills oficiais) e listava o perfil `REVIEWER` como nao implementado (esta implementado desde a trilha de revisao humana). Achado numa revisao de arquitetura, nao numa mudanca de codigo.
- `README.md` e `VALIDATION.md`: migration esperada corrigida pra `0012_request_attachments` (estava `0008`/`0010`); contagem de testes corrigida pra 90 (estava 63); catalogo de Agent Skills atualizado pra refletir visibilidade `OFFICIAL` por padrao (estava descrito como "escopadas por dono", default anterior a 2026-09-16).

### Contexto

- a pedido da autora, apos uma avaliacao do harness de RAG e da arquitetura pedida antes de iniciar o trabalho de nucleo comum de engenharia (CI/CD, Wiki): o gap mais concreto encontrado foi a validacao de RAG cobrir so 1 de 4 dominios, o que enfraquecia a defesa contra o risco de rubrica "so consome LLM via prompt, sem incorporar IA de fato" pra 3 das 4 skills oficiais.
- decisao de escopo, perguntada explicitamente: expandir a validacao pros 3 dominios restantes de uma vez (em vez de so documentar a lacuna, ou expandir 1 dominio por vez).
- limitacao registrada no proprio documento de evidencia: as fixtures novas foram escritas na mesma sessao que o gabarito de perguntas (ordem inversa do ideal -- gabarito extraido de documentacao pre-existente), o que provavelmente infla os numeros frente a uma base indexada organicamente ao longo do projeto.
- nenhum teste novo (`def test_`) foi adicionado -- os 2 testes existentes em `test_rag_quality.py` foram generalizados pra cobrir os 4 dominios, entao a contagem total da suite continua 90.

## 2026-09-21 - Anexo de documentos como contexto adicional da solicitacao

### Adicionado

- `RequestAttachment` (migration `0012_request_attachments`): documento anexado a uma `TechnicalRequest`, guardado como texto (nao blob binario) -- so extensoes de texto puro/codigo-fonte sao aceitas (`.txt`, `.md`, `.py`, `.js`, `.java`, `.json`, etc., ver `ATTACHMENT_ALLOWED_EXTENSIONS`); PDF/DOCX ficam de fora deliberadamente, evitando puxar dependencias novas de parsing de binario (e a superficie de seguranca que vem junto -- PDF malformado, DOCX tipo zip-bomb) sem avaliar isso a parte.
- `POST/GET /api/v1/requests/{id}/attachments` e `DELETE .../attachments/{attachment_id}`: upload multipart (ate `ATTACHMENT_MAX_BYTES`, 300 KB por padrao), listagem e remocao, todos escopados ao dono da solicitacao (`find_owned_request`, mesmo padrao de `add_request_context`).
- O conteudo dos anexos entra no prompt do planejador tecnico (`LLMPlanRequest.attachments_context`, `_build_safe_request` em `llm_service.py`) pelo mesmo pipeline de sanitizacao/truncamento/redacao que o resto do contexto -- nao e um caminho a parte que escapa da mascara de dados sensiveis.
- Anexar um documento e deliberadamente ortogonal a `complement_context`/qualificacao por tamanho minimo de contexto: nunca muda o status `AWAITING_CONTEXT` -> `QUALIFIED` sozinho (documentado no docstring de `add_attachment`), pra um arquivo pequeno nao virar uma segunda rota pra "qualificado" sem contexto textual de verdade.
- Frontend: campo de upload no passo 3 do wizard de Nova Solicitacao (arquivos selecionados localmente, enviados logo apos a solicitacao ser criada -- uma falha de upload nao bloqueia a criacao, so aparece como aviso na tela de orquestracao); secao "Documentos anexados" na tela de orquestracao pra listar/adicionar/remover anexos depois de criada.

### Contexto

- sugestao do Pedro no code review do PR #24 (wizard de Nova Solicitacao, ja mergeado): "gostaria de sugerir que seria de bom tom adicionar um campo de anexo de documento no contexto da orquestracao."
- decisao de escopo (texto puro, nao PDF/DOCX): extrair texto de formatos binarios exigiria novas dependencias de parsing com sua propria superficie de seguranca (documento malformado, entrada excessivamente grande apos descompactacao) que nao foi avaliada nesta rodada -- registrado como evolucao futura, nao esquecida.
- `python-multipart` adicionado a `requirements.txt` -- ja estava instalado como dependencia transitiva do `mcp`, mas o codigo novo depende dele diretamente (FastAPI `UploadFile`), entao passou a ser declarado explicitamente em vez de depender implicitamente de outra dependencia trazer ele.
- `MaxBodySizeMiddleware`/`MAX_REQUEST_BODY_BYTES` (docstring/comentarios): a alegacao de que "a aplicacao so recebe JSON, sem upload de arquivo" deixou de ser verdade com esse PR -- corrigida pra nao ficar desatualizada.
- 15 testes novos: `test_request_attachments.py` (upload/listagem/remocao, rejeicao por extensao/tamanho/vazio/nao-UTF-8, escopo por dono, ortogonalidade com qualificacao), `test_llm_service_build_request.py` (conteudo do anexo chega em `_build_safe_request`, rotulado por nome de arquivo, multiplos anexos concatenados em ordem) e 2 novos em `test_llm_prompts.py` (secao de anexos aparece/nao aparece no prompt conforme esperado).

## 2026-09-16 - Login com GitHub (OAuth), adicional ao email/senha

### Adicionado

- `GET /api/v1/auth/github/login` e `GET /api/v1/auth/github/callback` (`app/api/v1/endpoints/auth.py`): fluxo padrao de authorization code. O login gera um `state` aleatorio guardado num cookie curto (10 min) -- protecao CSRF propria do OAuth, ja que essa perna do fluxo e navegacao de pagina inteira, nao um fetch autenticado pelo CSRF da sessao. O callback valida o `state`, troca o `code` por um access_token, busca perfil/email verificado no GitHub, encontra ou cria a conta e abre uma sessao normal (mesmos cookies do login por senha) -- depois redireciona pro frontend.
- `app/services/github_oauth_service.py`: chamadas HTTP ao GitHub (`httpx`, adicionado a `requirements.txt`) e `find_or_create_user` -- casa por `github_id` primeiro; se o email verificado ja pertence a outra conta, recusa com erro claro (`github_email_in_use`) em vez de auto-linkar (essa app nao verifica email no cadastro por senha, entao auto-link seria uma via de account takeover).
- `users.password_hash` vira nullable (migration `0011_github_oauth`) -- contas GitHub nao tem senha. Novas colunas `github_id` (unico, indexado) e `avatar_url`. `authenticate_user` (`app/services/auth_service.py`) recusa login por senha numa conta GitHub-only com mensagem clara, gastando o mesmo tempo de uma verificacao real (`perform_dummy_password_check`) pra nao vazar pelo timing se a conta existe.
- `GITHUB_OAUTH_ENABLED` (padrao `false`), `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_OAUTH_REDIRECT_URI`, `FRONTEND_BASE_URL` -- novas settings, com validacao (client id/secret obrigatorios quando habilitado). Desabilitado por padrao: o projeto sobe normalmente sem OAuth App configurado, so o botao "Continuar com GitHub" some (e `/auth/github/*` responde 404).
- Frontend: botao "Continuar com GitHub" (`GitHubLoginButton.tsx`) nas telas de login e cadastro; `LoginPage.tsx` mostra mensagem de erro quando o backend redireciona com `?error=...`; avatar do GitHub substitui a inicial do nome na topbar quando disponivel (`AppShell.tsx`).
- `docs/integrations/github-oauth.md`: passo a passo pra criar o OAuth App no GitHub, diagrama do fluxo, tabela de codigos de erro.

### Contexto

- a pedido da autora: login adicional ao email/senha (nao substitui), mantendo a suite de testes existente intacta -- ela ja cria contas por senha na maioria dos testes.
- decisao de nao fazer auto-link de conta por email: risco real de account takeover dado que o cadastro por senha desta app nao verifica email hoje. Vincular manualmente e um fluxo que ainda nao existe.
- 7 testes novos em `test_github_oauth.py`, todos com as chamadas de rede ao GitHub mockadas via `monkeypatch` (diferente do padrao "sem mock" usado pros testes de LLM/RAG -- nao ha como automatizar o consentimento real de um usuario numa tela do GitHub).

## 2026-09-16 - USER pode executar orquestracoes; novas Agent Skills nascem OFFICIAL

### Corrigido

- `app/core/roles.py`: `LLM_EXECUTION_ROLES` (TECHNICIAN+ADMIN, usado pra tudo que tocava LLM) virou dois grupos distintos -- `ORCHESTRATION_ROLES = {USER, TECHNICIAN, ADMIN}` (rodar orquestracoes) e `SKILL_CATALOG_ROLES = {TECHNICIAN, ADMIN}` (curar o catalogo de Agent Skills). REVIEWER continua fora de `ORCHESTRATION_ROLES` -- separacao de funcoes, quem revisa nao e quem produz.
- `app/api/dependencies.py`: `require_technician` virou duas dependencies -- `require_orchestration_access` (novo grupo `ORCHESTRATION_ROLES`) e `require_skill_curator` (`SKILL_CATALOG_ROLES`, mesmo grupo de antes).
- `app/api/v1/endpoints/llm.py` (`/llm/status`, `/llm/invocations/{trace_id}`, `POST /llm/requests/{id}/plan`) e `app/api/v1/endpoints/agent_skills.py` (`POST /agent-skills/requests/{id}/execute`, `POST /agent-skills/requests/{id}/ask`): gate trocado de `require_technician` pra `require_orchestration_access` -- USER pode chamar agora. `create_skill`/`import_skill` (curadoria do catalogo) ficaram em `require_skill_curator`, sem mudanca de comportamento (continua TECHNICIAN/ADMIN).
- `app/agent_catalog/registry.py` (`register_skill`): `visibility` default muda de `PRIVATE` pra `OFFICIAL`. Sem essa mudanca, abrir o papel USER pra executar orquestracoes nao bastava na pratica -- toda skill nascia privada de quem importou, entao um USER recem-cadastrado batia em "Nenhuma Agent Skill... encontrada" (`NoAgentSkillsAvailableError`) mesmo com o papel liberado, porque `_resolve_target_skills` usa `viewer_id = technical_request.owner_id` e a skill so aparecia pro proprio importador. `owner_id` continua gravado pra atribuicao/auditoria; `visibility="PRIVATE"` continua existindo no modelo pra quem quiser registrar uma skill ainda em teste.

### Contexto

- a pedido da autora: "acho que o USER pode Executar orquestracao tambem pq se nao ele nao tem o pq de entrar na rede" -- o objetivo de fundo era ter um fluxo realmente usavel pro papel USER, nao so passar no gate de permissao.
- investigado e reportado antes de implementar: a liberacao de papel sozinha nao entregava o objetivo (catalogo ficava vazio pra USER por causa da visibilidade PRIVATE por padrao). 3 opcoes foram apresentadas (skills nascerem OFFICIAL / ADMIN publicar manualmente / deixar so o gate de papel) -- escolhida a primeira.
- testes: `test_llm.py` ganhou `test_regular_user_can_access_llm_status` (substituindo o antigo `test_regular_user_cannot_access_llm_status`) e `test_reviewer_cannot_access_llm_status` (prova que REVIEWER continua de fora); `test_custom_skills.py` teve `test_custom_skill_is_private_and_owner_scoped` reescrito pra `test_custom_skill_is_official_and_visible_to_everyone` (reflete o novo default) e ganhou `test_plain_user_can_execute_orchestration_on_others_official_skill`, provando o cenario real: USER nunca promovido executando contra uma skill importada por outra pessoa.
- risco assumido, ja documentado no README: com cadastro aberto por padrao (`ALLOW_REGISTRATION=true`) e cota diaria de tokens desligada por padrao (mudanca de 2026-09-14), qualquer pessoa que se cadastre agora pode gerar chamadas de LLM sem limite algum -- um deploy real exposto publicamente deve reativar a cota diaria e/ou fechar o cadastro.
- observado durante os testes (nao investigado a fundo, fora do escopo desta mudanca): alguns testes que chamam a OpenRouter de verdade com modelos `:free` falham de forma intermitente com resultado vazio/incompleto -- comportamento ja documentado nos comentarios de `openrouter_provider.py` (modelo free as vezes ignora o `strict json_schema`), reproduzido tanto antes quanto depois desta mudanca, portanto nao e uma regressao introduzida aqui.

## 2026-09-14 - Trilha de auditoria liberada para todo usuario autenticado, com escopo por dono

### Corrigido

- `GET /api/v1/audit/events` (`app/api/v1/endpoints/audit.py`): trocado o gate de `require_reviewer` (403 para USER/TECHNICIAN) para `get_current_user` -- qualquer papel autenticado pode consultar a trilha agora. REVIEWER/ADMIN continuam vendo o historico completo do sistema; USER/TECHNICIAN veem so eventos de solicitacoes que eles proprios criaram (filtro por `TechnicalRequest.owner_id`, aplicado tanto na listagem quanto nos contadores de estatisticas do dia).
- `frontend/src/components/layout/AppShell.tsx`: removido o item de menu "Auditoria" bloqueado (cadeado/disabled) para quem nao era REVIEWER/ADMIN -- o link fica sempre habilitado.
- `frontend/src/pages/AuditoriaPage.tsx`: aviso indicando escopo ("mostrando apenas as suas solicitacoes") quando o usuario logado nao e REVIEWER/ADMIN, pra nao parecer que a pagina esta vazia/quebrada.

### Contexto

- a pedido da autora: a pagina estava bloqueada demais (so REVIEWER/ADMIN), e ela queria liberar acesso pros demais usuarios verem sua propria trilha.
- opcao escolhida entre 3 alternativas apresentadas: abrir pra todo usuario autenticado (incluindo USER, que hoje nao tem nenhum papel de execucao), escopado as proprias solicitacoes -- nao abrir a trilha completa do sistema pra quem nao e revisor/admin, pra nao vazar dado de outros usuarios.
- verificado contra a RFC do projeto (`docs/rfc/...md`): RF15 fala em "usuarios autorizados" (termo generico, nao restrito a REVIEWER/ADMIN) consultarem o historico, e a jornada de usuario padrao descrita no documento ja inclui "consulta a resposta consolidada e, posteriormente, pode auditar o historico de decisoes" como parte do fluxo normal -- a mudanca fica mais aderente a especificacao formal, nao e um desvio dela.
- 3 testes atualizados/adicionados em `test_audit.py`: o teste antigo que esperava 403 pra USER virou dois novos (USER ve as proprias, USER nao ve as de outro USER) e um teste de 401 genuino (sem sessao) substituiu a checagem de role que nao existia mais.

## 2026-09-14 - Remove tetos de token que limitavam a orquestracao por padrao

### Corrigido

- `LLM_MAX_OUTPUT_TOKENS` (`app/core/config.py`, `app/llm/providers/openrouter_provider.py`, `app/llm/providers/openai_provider.py`): padrao muda de 3000 para `0` (sem teto) -- os providers agora omitem `max_tokens`/`max_output_tokens` da chamada quando o valor e 0, deixando o modelo usar seu proprio maximo. Esse teto fixo ja tinha causado respostas vazias (`finish_reason: length`) em modelos de raciocinio como `gpt-5-mini`, que gastam parte do orcamento em "pensamento" interno antes do conteudo visivel -- exatamente o tipo de limitacao que truncava planos de orquestracao. Validador atualizado para aceitar `0` ou `>= 128`.
- `LLM_DAILY_TOKEN_LIMIT_PER_USER` (`app/core/config.py`): padrao muda de 150000 para `0` (sem limite) -- a checagem de cota diaria continua existindo em `generate_technical_plan`, so fica desligada por padrao.

### Contexto

- a pedido da autora: a limitacao de tokens estava restringindo a orquestracao multi-agente.
- ambos os tetos ja suportavam `0 = sem limite`; a mudanca foi so de valor padrao (e, no caso do teto por chamada, passar a omitir o parametro em vez de enviar um numero fixo).
- **risco assumido**: sem `LLM_DAILY_TOKEN_LIMIT_PER_USER` a protecao de custo contra uso excessivo da assinatura OpenRouter fica desligada por padrao; quem fizer deploy real deve reativar essa variavel com um valor calibrado se quiser esse disjuntor de volta.
- 2 asserções em `test_admin.py` que assumiam o antigo padrao positivo (`daily_token_limit_per_user > 0`) foram atualizadas para `== 0`; os testes em `test_llm.py` já definiam o limite via `monkeypatch` e não foram afetados.

## 2026-09-08 - Limpa artefatos de citacao do Documento_de_referencia.md

### Corrigido

- Removidas as 76 ocorrencias de marcadores de citacao nao processados (sequencias `citeturnNsearchM`/`citeturnNviewM` usando caracteres da Private Use Area do Unicode como delimitadores invisiveis -- por isso nao apareciam em buscas de texto simples antes de investigar os bytes crus do arquivo) que restavam de uma sessao de pesquisa anterior.
- Adicionado aviso no topo do documento deixando explicito que o conteudo (arquitetura "Agentic Control Plane", integracao com Hermes/GSD Pi) e especulativo e nao implementado no codigo -- a RFC continua sendo a especificacao vigente do projeto.

### Contexto

- item aprovado pela autora durante a revisao de documentos artificiais/desatualizados do repositorio;
- verificado: diff minimo (so as linhas com marcador realmente mudaram, nada de formatacao pre-existente foi tocado -- confirmado comparando contagem de espacos duplos antes/depois, identica) e zero marcador remanescente (bytes crus checados diretamente, nao so busca de texto).

## 2026-09-08 - Auditoria de seguranca P2/P3: VALIDATION.md atualizado, limite de corpo HTTP, limpeza de diretorios fantasma

### Adicionado

- `MaxBodySizeMiddleware` (`app/core/middleware.py`, novo `MAX_REQUEST_BODY_BYTES`, padrao 2MB): rejeita pelo `Content-Length` declarado, antes de qualquer rota le-lo -- a aplicacao so recebe JSON, sem upload de arquivo, entao o teto cobre folgadamente o maior payload legitimo hoje.
- 2 testes cobrindo o middleware (corpo grande rejeitado com 413, corpo normal segue pro fluxo de validacao de sempre).

### Corrigido

- `VALIDATION.md` reescrito por completo -- estava parado na migration `0003` e citava `LLM_PROVIDER=mock`, removido do codigo ha muito tempo; agora reflete o estado real (migration `0010`, 4 perfis, sem mock, 63 testes) e referencia `docs/validation/evidence/` em vez de duplicar o conteudo.
- Removidos dois diretorios fantasma da raiz do repositorio, nunca rastreados pelo git: `doc/` (legado, ja vazio -- as imagens do RFC ja tinham sido movidas pra `docs/rfc/imagens/` antes desta sessao) e um diretorio cujo nome comecava literalmente com aspas (`"docs`, sobra de um comando mal executado). De quebra, isso eliminou um aviso recorrente do git ("could not open directory...") que aparecia em todo comando `git status` desde o inicio da sessao -- a pasta fantasma confundia a leitura do diretorio real `docs/`.

### Contexto

- itens P2 e P3 do plano de fechamento tecnico/seguranca aprovado pela autora;
- os diretorios fantasma nunca estiveram no historico do git (`git ls-files` confirmou 0 arquivos rastreados em ambos) -- a remocao nao gera diff nenhum, so limpa a arvore de trabalho;
- verificado com `ruff`/`mypy app` (limpos) e suite completa do backend (real, sem mock).

## 2026-09-08 - Auditoria de seguranca P1 (parte 2): Swagger desligado em producao, rate limiter confia em proxy so quando configurado

### Corrigido

- `app/main.py`: `docs_url`/`redoc_url`/`openapi_url` desligados quando `ENVIRONMENT=production`, independente da porta do backend estar exposta -- corrige o achado real (Swagger acessivel em producao) sem mudar o fluxo de desenvolvimento local (a porta 8000 continua exposta, `localhost:8000/docs` continua funcionando em dev).
- `app/core/rate_limit.py` (`resolve_client_ip`, novo): o rate limiter so confia no cabecalho `X-Forwarded-For` quando o IP que abriu a conexao direta estiver na lista `TRUSTED_PROXY_IPS` (nova config, vazia por padrao) -- caso contrario continua usando o IP direto de hoje. Evita que uma requisicao direta forje o cabecalho pra escapar do proprio limite.
- `frontend/nginx.conf`: passa a enviar `X-Forwarded-For` (faltava) -- pre-requisito pro item acima funcionar quando `TRUSTED_PROXY_IPS` for configurado num deploy real.
- `SECURITY.md`: secao de autorizacao atualizada para os 4 perfis reais (estava desatualizada, ainda listava 3 e dizia que REVIEWER nao existia); documenta o novo comportamento do rate limiter e do desligamento do Swagger.

### Contexto

- restante do item P1 do plano de fechamento tecnico/seguranca; a correcao original prevista (fechar a porta 8000, confiar sempre no proxy) foi revista em conversa direta -- fechar a porta quebraria o acesso local ao Swagger sem necessidade, e confiar sempre no X-Forwarded-For sem allowlist seria uma forma nova de burlar o rate limit;
- verificado com `ruff`/`mypy app` (limpos), 6 testes novos/atualizados em `test_config.py` (bloqueio de producao insegura + resolucao de IP com e sem proxy confiavel), suite completa do backend, e verificacao real via Docker Compose: `/docs` responde 200 em dev, login via nginx com o novo cabecalho funciona normalmente.

## 2026-09-08 - Auditoria de seguranca P1: sobe react-router-dom para v7 (CVEs)

### Corrigido

- `react-router-dom` 6.28.0 -> 7.18.3. A auditoria original recomendava so um patch dentro da 6.x (6.30.6), mas CVEs novas identificadas nesta verificacao (redirecionamento aberto via backslash em `<Link>`/`useNavigate`, injecao arbitraria de construtor via `deserializeErrors()` na hidratacao SSR) passaram a afetar toda a linha 6.x ate 7.17.0 -- so a v7 corrige de fato. App usa o modo declarativo (`<Routes>`/`<Route>`/`<Link>`/`useNavigate`), compativel sem mudanca de codigo.
- `vite` 5.4.11 -> 5.4.21 (patch, mesma major): corrige 3 vulnerabilidades do servidor de desenvolvimento (bypass de `server.fs.deny`, path traversal em source maps, disclosure de hash NTLMv2 no Windows) -- nao afetam o build de producao servido pelo nginx, so o `vite dev` local.

### Contexto

- item P1 do plano de fechamento tecnico/seguranca aprovado pela autora;
- residual conhecido, aceito por ora: `esbuild <=0.24.2` (moderado, GHSA-67mh-4wv8-2f99) continua no audit -- so corrige com Vite 6+/8+ (mudanca de major, fora do escopo deste item; tambem dev-server-only, nao afeta producao);
- verificado com `tsc -b`, `npm run build` (limpos), e um smoke test funcional real via Playwright cobrindo todas as rotas da aplicacao, navegacao profunda, voltar/avancar do navegador e logout -- sem erro de console real, so o 401 esperado apos logout.


## 2026-09-08 - Auditoria de seguranca P0: aplicacao recusa subir em producao sem COOKIE_SECURE

### Adicionado

- `Settings.validate_production_hardening` (`app/core/config.py`): falha no boot se `ENVIRONMENT=production` e `COOKIE_SECURE=false` -- antes disso era so uma recomendacao em `SECURITY.md`, sem nada aplicando de fato.
- `.env.production.example`: template de producao com os valores minimos exigidos (`ENVIRONMENT=production`, `COOKIE_SECURE=true`, `ALLOW_REGISTRATION=false`, dominio real em `CORS_ORIGINS`/`TRUSTED_HOSTS`), todo valor sensivel marcado `CHANGE-ME`. Adicionado ao `.gitignore` como excecao (igual `.env.example`) para nao ser tratado como segredo.
- `backend/tests/test_config.py`: 3 testes cobrindo o validador (bloqueia producao insegura, aceita producao correta, nao afeta desenvolvimento) -- rapidos, sem chamada real de LLM.

### Contexto

- item P0 do plano de fechamento tecnico/seguranca (auditoria completa em Etapas 1-4, aprovado pela autora antes de qualquer mudanca de codigo);
- achado original: nenhuma configuracao de produção real existia no repositorio, e `COOKIE_SECURE=false` era o padrao sem nenhum enforcement -- se a stack subisse "em producao" como estava, cookies de sessao/CSRF trafegariam em texto claro;
- verificado com `ruff`/`mypy app` (limpos) e teste manual direto (`ENVIRONMENT=production COOKIE_SECURE=false` realmente bloqueia na inicializacao, com a mensagem de erro certa).

## 2026-09-08 - Rede de agentes, fase 1: skills criadas por usuario (fundacao)

### Adicionado

- `AgentSkill` ganha `owner_id`, `visibility` (OFFICIAL/PRIVATE/CLAN/PUBLIC) e `persona_instructions` (migration `0010_agent_skill_ownership`) -- as 4 skills oficiais existentes viram `visibility=OFFICIAL` automaticamente, sem mudanca de comportamento.
- `GenericSkillExecutor` (`app/agent_catalog/tool_interface.py`) + `generic_skill_server.py` (novo servidor MCP real): qualquer skill criada por um usuario roda por esse caminho generico, guiada pela `persona_instructions` do proprio manifesto, sem precisar de uma classe `SkillExecutor` dedicada por skill -- os 4 executores oficiais continuam intactos.
- `POST /agent-skills` (endpoint ja existente, "criacao assistida") agora grava `owner_id`/`visibility=PRIVATE`; toda a cadeia de selecao de skills (`_resolve_target_skills`, `select_skills_for_domain`, `list_active_skills`, `list_all_skills`, follow-up direcionado) passa a ser escopada por dono -- um usuario nunca ve nem aciona a skill privada de outro.
- `GET /agent-skills/{id}` retorna 404 para skill privada de outro usuario (antes nao tinha nenhum escopo).
- Frontend: `frontend/src/pages/AgentSkillCreatePage.tsx` -- wizard de 3 passos (Identidade, Persona, Comportamento esperado) pra criar uma skill sem precisar colar um `modelo.md` cru; `TagListField` (componente reutilizavel) padroniza os campos de lista. `AgentSkillsPage` ganha os 3 agentes fixos do ecossistema (Orquestrador, Conselheiro -- o Advisory Agent/Quality Gate ja existente, batizado agora -- e Orientador de Interacao) como cards no topo, e um selo "Oficial do ecossistema" / "Minha skill · privada" em cada card de skill.

### Corrigido

- Bug de regressao real (nao instabilidade) introduzido durante esta mudanca: `ask_follow_up_question` (pergunta direcionada a um dominio especifico) chamava `select_skills_for_domain` sem `viewer_id`, o que passou a excluir as proprias skills importadas do usuario assim que elas viraram `PRIVATE` por padrao -- pego pela suite real antes do commit, nao em producao.

### Contexto

- pedido direto da autora: arquitetura de "rede de agentes" com fase 1 (fundacao) definida em conversa -- executor generico por manifesto (nao codigo por skill), skill nasce privada, escopo por dono desde ja mesmo sem a tela de rede completa (fases 2 e 3 ainda por vir: Contestador/QA e clas/publico);
- decisao tecnica verificada no codigo antes de implementar: os 4 executores oficiais ja eram quase identicos entre si (so o rotulo de dominio mudava), confirmando que um executor generico era viavel sem reescrever nada dos 4 existentes;
- verificado com `ruff`/`mypy app` (limpos), suite completa do backend (real, sem mock) incluindo 2 testes novos (`test_custom_skills.py`), `tsc -b` (frontend) e fluxo real via Playwright + Docker Compose: catalogo com os 3 agentes fixos, wizard completo, skill criada aparecendo como "Minha skill · privada", e um bug de layout (badge "obrigatorio" quebrando linha) corrigido antes do commit.

## 2026-08-30 - Corrige navegacao colada no cabecalho em telas medias (<=820px)

### Corrigido

- `frontend/src/styles/workspace.css`: no breakpoint `max-width: 820px`, a barra lateral vira uma navegacao horizontal (`.workspace-sidebar { position: static }`), mas ficava sem nenhuma separacao visual do cabecalho logo abaixo -- a borda direita da versao desktop nao faz sentido nesse layout horizontal. Adicionada `border-bottom` + sombra sutil no lugar da borda direita, e o cabecalho deixa de ser `position: sticky` nesse breakpoint (evita que ele deslize por cima da navegacao ao rolar a pagina, ja que os dois agora sao blocos normais empilhados na mesma coluna).

### Contexto

- reportado pela autora com um print real do Pedro (revisor) testando em uma largura de tela media -- a navegacao aparecia "em cima do cabecalho";
- reproduzido de proposito com Playwright em varias larguras (700-1000px) pra achar o breakpoint exato (820px) antes de corrigir;
- verificado visualmente nas mesmas larguras apos a correcao, incluindo com a pagina rolada, sem sobreposicao em nenhum caso;
- `npx tsc -b` limpo (mudanca e so CSS).

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
