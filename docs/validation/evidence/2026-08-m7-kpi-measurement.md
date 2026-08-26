# Evidência de Validação - Medição de KPIs (M7)

**Consolidação documental:** 26/08/2026
**Escopo:** RFC seção 1.6 (Tabela 1: KPIs da Arquitetura) — primeira rodada de medição, marco M7 (Validação e Avaliação)

## Contexto

Esta é a primeira medição real dos KPIs da RFC, feita rodando 5 cenários de análise técnica ponta a ponta contra o ambiente Docker Compose (PostgreSQL real, backend real, OpenRouter real — sem provedor mock, que foi removido). Todos os 4 domínios de Agent Skill (Código Legado, Regras de Negócio, Arquitetura de Software, Segurança da Informação) foram importados e usados. Nenhuma base de conhecimento foi ingerida para os cenários, então o nível de confiança das respostas ficou BAIXO em todos os casos (evidência insuficiente por desenho — isso é esperado e não é o alvo desta medição).

**Importante:** o código medido ainda não está em `main` — vive nas branches empilhadas (PRs #2–#16). Esta é uma medição de validação técnica antecipada, não a medição formal final do M7 (que deve ser repetida após o merge).

## Resultado por KPI

| KPI | Meta | Medido | Status |
|---|---|---|---|
| Tempo Médio de Resposta | ≤ 10s | **11,8s** (LLM) / **13,9s** (Agent Skill, inclui overhead de orquestração) | ❌ **Não atingido** |
| Rastreabilidade | 100% dos fluxos | **100%** (15/15 solicitações com Trace ID e eventos vinculados) | ✅ Atingido |
| Articulação entre Domínios | ≥ 3 agentes | **3 agentes numa mesma análise**, comprovado por teste automatizado | ✅ Atingido (evidência anterior) |
| Extensibilidade Plug-and-Play | 1 skill integrada | **1 skill (Segurança da Informação)** acoplada sem alterar o núcleo do Orquestrador | ✅ Atingido (evidência anterior) |
| Taxa de Sucesso End-to-End | ≥ 80% | **100%** das execuções técnicas (8/8 invocações de Agent Skill e de LLM concluídas sem falha) — mas **0/5** solicitações chegaram a `COMPLETED` sem exigir revisão humana | ⚠️ **Ambíguo — ver limitação abaixo** |
| Qualidade do Manifesto | ≥ 80% válidos | **100% de classificação correta** do validador (10/10) — ver nota metodológica abaixo antes de ler isso como "80%" | ⚠️ **Ver nota metodológica** |
| Redução do Tempo de Análise | ≥ 30% | não mensurável nesta fase — benchmarks publicados dão proporção de tempo, não duração absoluta comparável | ⏳ **Não mensurável sem estudo controlado** |

## Detalhamento

### Tempo Médio de Resposta (❌ não atingido)

8 invocações reais (LLM + Agent Skill) contra `nvidia/nemotron-3-super-120b-a12b:free`:

| Métrica | Valor |
|---|---|
| Latência média (LLM) | 11.838 ms |
| Latência mediana (LLM) | 8.954 ms |
| Latência mínima | 5.250 ms |
| Latência máxima | 25.285 ms |
| Latência média (Agent Skill, inclui overhead de orquestração/MCP) | 13.872 ms |

A meta de ≤10s não foi atingida com o modelo gratuito padrão. Isso é uma limitação conhecida de modelos `:free` compartilhados (throughput menor, fila compartilhada) — a própria variação entre latência mínima (5,3s) e máxima (25,3s) mostra a instabilidade. Duas saídas possíveis para a próxima rodada: (a) medir com um modelo pago mais rápido antes de declarar a meta inatingível, ou (b) revisar a meta de 10s à luz do trade-off custo-zero vs. latência assumido pela PoC.

### Rastreabilidade (✅ atingido)

15/15 solicitações técnicas registradas nesta sessão têm `Trace ID` e pelo menos um evento de orquestração vinculado — 100% de cobertura, por desenho arquitetural (todo `TechnicalRequest` gera um Trace ID na criação).

### Articulação entre Domínios e Extensibilidade (✅ atingidos, evidência já existente)

Não remedidos nesta rodada — já comprovados por teste automatizado e documentados em:
- `backend/tests/test_agent_skills.py::test_execute_orchestration_step_runs_three_skills_in_one_analysis`
- `docs/validation/evidence/2026-08-plug-and-play-extensibility.md`

### Taxa de Sucesso End-to-End (⚠️ ambíguo)

Todas as 8 invocações técnicas (Agent Skill + LLM) completaram sem falha de sistema — 100% de sucesso técnico. Porém, nenhuma das 5 solicitações chegou ao status `COMPLETED`; todas pararam em `VALIDATING`, porque o Quality Gate sinalizou necessidade de revisão humana (confiança BAIXO, já que nenhuma base de conhecimento foi ingerida para os cenários de teste).

**A RFC não define explicitamente** se "sucesso end-to-end" significa (a) o fluxo executar sem erro técnico até uma resposta consolidada, ou (b) o Quality Gate aprovar sem exigir revisão humana. Essas são medidas bem diferentes:
- Interpretação (a): **100%** — meta atingida.
- Interpretação (b): **0%** — meta não atingida, mas isso reflete a ausência de evidência (RAG vazio), não uma falha arquitetural.

Recomenda-se decidir essa definição antes da medição formal, idealmente rodando os cenários com uma base de conhecimento real ingerida (a PoC tem fixtures em `backend/app/rag/fixtures/legacy_billing/` e `seed_knowledge_base.py` para isso).

### Qualidade do Manifesto (⚠️ nota metodológica importante)

Submeti um lote de 10 manifestos contra `POST /agent-skills/import` na API real: os 4 fixtures conhecidos como válidos (Código Legado, Regras de Negócio, Arquitetura, Segurança) mais 6 variações derivadas do fixture de Código Legado, cada uma com exatamente um defeito realista de autoria:

| Caso | Defeito injetado | Resultado |
|---|---|---|
| `missing_security_rules_section` | Remove a seção "Regras de Segurança" | ✅ Rejeitado, mensagem específica |
| `unrecognized_domain` | Domínio "Segurança Cibernética" (não existe) | ✅ Rejeitado, lista os domínios válidos |
| `missing_version_field` | Remove o campo "Versão" da Identificação | ✅ Rejeitado, mensagem específica |
| `empty_capabilities_section` | Seção "Capacidades" vazia | ✅ Rejeitado, mensagem específica |
| `missing_title_heading` | Remove o heading `# Nome do Agente` | ✅ Rejeitado, mensagem específica |
| `missing_operating_limits` | Remove a seção "Limites de Atuação" | ✅ Rejeitado, mensagem específica |

**Resultado bruto: 4/10 manifestos válidos (40%)** — abaixo da meta de 80%. **Mas essa leitura direta é enganosa**: montei o lote propositalmente com 60% de defeitos para testar a cobertura do validador, não para simular o que um usuário real submeteria. A leitura correta é outra: **10/10 classificações corretas** — os 4 manifestos genuinamente válidos foram aceitos, e os 6 defeitos foram rejeitados com mensagens específicas e acionáveis (não uma mensagem genérica). Isso é evidência de que o validador funciona bem, não de que "40% dos manifestos são válidos".

**A meta de "≥80% válidos" da RFC não define a metodologia de amostragem** — não fica claro se o KPI mede (a) a precisão do validador contra uma amostra conhecida (o que medi: 100%), ou (b) a taxa de sucesso de submissões orgânicas de usuários reais (o que exigiria dados de uso real, que não existem ainda nesta PoC). Essa definição precisa ser decidida antes de declarar o KPI atingido ou não.

### Redução do Tempo de Análise (⏳ não mensurável com os dados disponíveis)

Exige uma linha de base de tempo de análise manual (sem a PoC) para comparar contra o tempo medido pela orquestração. Não há esse número em nenhum lugar do projeto — nem a RFC (Seção 1.1/1.2, Apêndice A) quantifica tempo, só descreve o problema qualitativamente ("gargalos", "retrabalho", "degradação de contexto").

Pesquisei benchmarks publicados sobre tempo de desenvolvedor gasto entendendo código/sistemas legados, como possível linha de base indireta:

- Estudo citado pela Krugle: desenvolvedores gastam 11–30% do tempo corrigindo dívida técnica, e cerca de metade disso só entendendo o código-fonte ([Sourcegraph, "Legacy Code Modernization"](https://sourcegraph.com/blog/legacy-code-modernization)).
- Outro benchmark: ~5% do tempo escrevendo código novo, ~20% modificando código legado, **até 60% só entendendo o sistema existente** ([IN-COM Data Systems](https://www.in-com.com/blog/developer-experience-dx-metrics-for-legacy-codebases-beyond-surveys-and-sentiment-analysis/)).
- Levantamento mais amplo: desenvolvedores gastam entre 58% e 70% do tempo entendendo código-fonte ([Devox Software](https://devoxsoftware.com/blog/how-ai-powered-tools-accelerate-legacy-code-understanding-and-refactoring/)).

**Esses números não fecham o KPI.** Eles descrevem *proporção do tempo de trabalho* (ex.: "60% de uma semana"), não a *duração absoluta* de uma tarefa pontual como os cenários testados nesta rodada (análise de um impacto técnico específico, ~12–14s de resposta automatizada). Calcular uma "redução de X%" comparando segundos de resposta da PoC contra uma fração de jornada de trabalho seria uma conta inválida — as duas grandezas não são comparáveis sem uma linha de base de duração absoluta para a MESMA tarefa.

O que os benchmarks reforçam é a tese central da RFC (Seção 1.1): entendimento/análise domina o tempo do desenvolvedor, o que justifica a arquitetura, mas não substitui uma medição própria. A medição correta deste KPI exige um **estudo controlado**: cronometrar a mesma tarefa de análise, feita por uma pessoa sem a PoC e com a PoC, idealmente repetido com múltiplas pessoas/tarefas para ter validade estatística. Isso é trabalho de campo genuíno (não decidível por pesquisa bibliográfica) e fica registrado como pendência explícita para uma próxima rodada do M7.

## Bug real encontrado durante esta medição

Rodar contra PostgreSQL real (em vez do SQLite usado pela suíte de testes) expôs um bug latente: `agent_skills.output_contract_ref` era `VARCHAR(200)`, mas o conteúdo real de **todos os 4 manifestos de fixture** tem 205 caracteres nesse campo — SQLite nunca aplica limite de tamanho de coluna, então nenhum teste pegou isso. Corrigido na migration `0007_widen_contract_refs` (colunas `input_contract_ref`/`output_contract_ref` ampliadas para `VARCHAR(500)`).

Isso reforça o princípio já registrado em `docs/validation/evidence/2026-08-foundation-validation.md`: "o uso de SQLite serve como verificação estrutural... a validação final deve ser repetida no PostgreSQL."

## Ambiente da medição

- `docker compose up --build` (rebuild completo, PostgreSQL real, sem mock)
- Modelo: `nvidia/nemotron-3-super-120b-a12b:free` (padrão configurado)
- 5 cenários de análise técnica, cobrindo 1 a 3 domínios cada
- 4 Agent Skills importadas (Código Legado, Regras de Negócio, Arquitetura de Software, Segurança da Informação)

## Limitações deste registro

- Medição feita contra as branches ainda não mergeadas em `main` — deve ser repetida após o merge da pilha de PRs.
- Nenhuma base de conhecimento foi ingerida; a Taxa de Sucesso e o nível de confiança das análises refletem isso, não a qualidade do pipeline em si.
- Amostra pequena (5 solicitações, 8 invocações; 10 manifestos) — suficiente para uma primeira leitura, não para conclusões estatísticas.
- Qualidade do Manifesto: a RFC não define a metodologia de amostragem (precisão do validador vs. taxa de submissões orgânicas) — medi a primeira (100%), a segunda não é medível sem dados de uso real.
- Redução do Tempo de Análise: benchmarks publicados sobre tempo de compreensão de código legado (58-70% do tempo do desenvolvedor) foram pesquisados, mas descrevem proporção de jornada, não duração absoluta comparável à resposta da PoC — o KPI exige um estudo controlado (mesma tarefa, com e sem a ferramenta), que é trabalho de campo, não decidível por pesquisa bibliográfica.
- Este documento não substitui a análise de viabilidade final exigida pelo M7.
