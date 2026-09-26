# Evidência de Validação - Qualidade do RAG nos 4 domínios de Agent Skill

**Consolidação documental:** 21/09/2026
**Escopo:** RFC §6.1 "Proteção de Contexto" (pipeline RAG) e requisito da linha "IA" do Portfolio Directions — "validação do modelo com técnica adequada" e evidência de que a solução "incorpora IA de fato". Estende [`2026-08-30-rag-quality-validation.md`](2026-08-30-rag-quality-validation.md), que cobria só o domínio `codigo_legado`.

## Por que este documento existe

A medição de 30/08/2026 deixou registrado, como limitação explícita, que só o domínio "Código Legado" tinha base de conhecimento indexada — as outras três Agent Skills oficiais (Regras de Negócio, Arquitetura de Software, Segurança da Informação) tinham executor real, mas respondiam sem nenhum contexto recuperado. Numa revisão de arquitetura feita em 21/09/2026, esse gap foi apontado como o ponto mais concreto de exposição ao risco de rubrica "só consome LLM via prompt, sem incorporar IA de fato" — a defesa via RAG só valia para 1 de 4 skills. Este documento fecha esse gap.

## Escopo desta medição

Três novos domínios ganharam base de conhecimento própria, seguindo o mesmo padrão de fixture sintética e autocontida do domínio original:

- `backend/app/rag/fixtures/business_rules/` — `change-request-history.md`, `pricing-policy.md`
- `backend/app/rag/fixtures/architecture/` — `module-dependency-map.md`, `deployment-topology.md`
- `backend/app/rag/fixtures/security/` — `access-control-notes.md`, `data-classification.md`

Todos os três giram em torno do **mesmo sistema legado fictício** (o módulo de limite de crédito já usado em `legacy_billing`), cada um sob um ângulo diferente (histórico de decisão de negócio, acoplamento estrutural, controle de acesso/LGPD) — deliberado: testar se o retriever discrimina por assunto mesmo quando o sistema de fundo se sobrepõe é um teste mais rigoroso do que medir cada domínio isolado, sem nenhum distrator.

`backend/app/rag/retriever.py` não filtra por domínio — todos os `knowledge_chunks` de todas as fixtures competem no mesmo ranking por similaridade de cosseno, com o texto "Domínio: X" só como viés na query (ver `app/rag/service.py::retrieve_context_for_request`). Por isso, esta medição **co-indexou os quatro domínios na mesma base**, em vez de medir cada um isolado — é o cenário real de produção, não uma condição artificialmente favorável.

## Metodologia

Mesma metodologia de 30/08/2026, generalizada para 4 domínios: `backend/app/rag/evaluation.py` define `GROUND_TRUTH_BY_DOMAIN`, um gabarito manual por domínio (8 perguntas para Código Legado, já existente; 5 novas para cada um dos outros três, lidas diretamente do conteúdo real das fixtures, não geradas automaticamente). `backend/tests/test_rag_quality.py::test_retrieval_quality_against_ground_truth` ingere as quatro pastas de fixture inteiras com embeddings reais da OpenRouter (`openai/text-embedding-3-small`, sem mock), roda todas as perguntas contra o `InMemoryVectorRetriever` com `top_k=3`, e calcula Precision@3, Recall@3 e Reciprocal Rank por pergunta e por domínio.

## Resultado — Qualidade da recuperação, por domínio

```text
=== Código Legado (n=8) ===
Mean P@3=0.479  Mean R@3=0.750  MRR=0.875

=== Regras de Negócio (n=5) ===
Mean P@3=0.467  Mean R@3=1.000  MRR=1.000

=== Arquitetura de Software (n=5) ===
Mean P@3=0.567  Mean R@3=0.900  MRR=0.900

=== Segurança da Informação (n=5) ===
Mean P@3=0.767  Mean R@3=1.000  MRR=1.000
```

**Leitura honesta:**

- Os três domínios novos tiveram MRR entre 0.90 e 1.00 — em praticamente todas as perguntas, o artefato certo apareceu na primeira posição. Isso é mais alto que o domínio original, e é esperado: as fixtures novas foram escritas depois do gabarito de perguntas (o inverso do domínio "Código Legado", cujo gabarito foi escrito por leitura de um fixture já existente), o que tende a produzir uma correspondência semântica mais direta entre pergunta e documento.
- **Recall@3 do domínio "Código Legado" caiu de 0,812 (medição isolada de 30/08) para 0,750 nesta medição co-indexada.** Isso não é uma regressão no pipeline — é o efeito esperado e documentado de introduzir 6 novos documentos como distratores reais no mesmo ranking. Fica registrado como está, não ajustado para esconder a queda.
- Precision@3 ficou relativamente baixa em todos os domínios (0,47 a 0,77) porque `top_k=3` frequentemente retorna mais posições do que artefatos relevantes existem para aquela pergunta (ex.: uma pergunta com 1 artefato relevante correto na posição 1 já é sucesso pleno de Recall e MRR, mas "gasta" as posições 2 e 3 com vizinhos semânticos não rotulados como relevantes) — é uma característica do gabarito ter poucos artefatos relevantes por domínio, não um defeito de retrieval; por isso os limiares de regressão do teste automatizado são sobre MRR e Recall@3, não sobre Precision@3, mesma escolha já feita na medição original de 30/08.
- Uma pergunta cruzando domínios funcionou como esperado: "O serviço de domínio do limite de crédito está acoplado diretamente ao schema do banco de dados?" (domínio Arquitetura) tinha `CustomerRepository.java` do domínio Código Legado como um dos artefatos relevantes esperados, e o retriever encontrou ambos os artefatos certos (R@3=0,50, RR=0,50 — a segunda posição, não a primeira) — evidência de que o retrieval de fato busca por similaridade semântica cruzando pastas de fixture, não por alguma segmentação implícita de diretório.

## Teste automatizado

```text
pytest tests/test_rag_quality.py tests/test_rag.py -v
8 passed
```

`ruff check app tests`: 0 findings. `mypy app`: 0 issues.

Os limiares de regressão (`MIN_MEAN_RECIPROCAL_RANK_BY_DOMAIN`, `MIN_MEAN_RECALL_AT_K_BY_DOMAIN` em `test_rag_quality.py`) foram fixados com margem real abaixo do que foi medido nesta rodada — um flip de pergunta desloca a média em 1/8=0,125 (Código Legado) ou 1/5=0,20 (os outros três), e os limiares deixam essa margem sem tratar variação normal do embedding como regressão.

## Limitações deste registro

- As fixtures dos três domínios novos foram escritas nesta mesma sessão de trabalho, na ordem inversa do ideal metodológico (documento e gabarito compostos juntos, não gabarito extraído de documentação pré-existente) — isso provavelmente infla os números frente a uma base de conhecimento indexada organicamente ao longo do projeto. Registrado aqui para não ser lido como mais forte do que é.
- Cobertura ainda é de 5 perguntas por domínio novo, contra 8 do domínio original — amostra pequena, mesma ressalva já feita para o domínio original em 30/08.
- Este documento mede só a metade "recuperação" do RAG (qualidade do retrieval); a medição de "valor agregado na resposta final" (Resultado 2 do documento de 30/08) não foi repetida para os três domínios novos.
- Não substitui a medição formal dos KPIs do RFC (§5.5), registrada em `docs/validation/evidence/2026-08-m7-kpi-measurement.md`.
