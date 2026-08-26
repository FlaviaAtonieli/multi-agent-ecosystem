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
| Qualidade do Manifesto | ≥ 80% válidos | não medido nesta rodada | ⏳ Pendente |
| Redução do Tempo de Análise | ≥ 30% | não medido nesta rodada | ⏳ Pendente |

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

### Qualidade do Manifesto e Redução do Tempo de Análise (⏳ pendentes)

Não medidos nesta rodada:
- **Qualidade do Manifesto** exige um lote de manifestos (válidos e inválidos) para calcular a taxa de aprovação — precisa de uma amostra definida (manifestos reais submetidos, não só os 4 de fixture já validados).
- **Redução do Tempo de Análise** exige uma linha de base de tempo de análise manual (sem a PoC) para comparar — é uma medida de metodologia (estimativa/entrevista), não só de código.

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
- Amostra pequena (5 solicitações, 8 invocações) — suficiente para uma primeira leitura, não para conclusões estatísticas.
- Qualidade do Manifesto e Redução do Tempo de Análise ainda não têm metodologia de medição definida.
- Este documento não substitui a análise de viabilidade final exigida pelo M7.
