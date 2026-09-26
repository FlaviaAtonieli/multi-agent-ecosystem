# Evidência de Validação - Qualidade do RAG

**Consolidação documental:** 30/08/2026
**Escopo:** RFC §6.1 "Proteção de Contexto" (pipeline RAG) e requisito da linha "IA" do Portfolio Directions — "validação do modelo com técnica adequada" e evidência de que a solução "incorpora IA de fato" (não apenas consome uma API de LLM por prompt).

## Por que este documento existe

O item estava registrado como pendência de alto risco em `docs/gestao/agenthub-epicos-historias.csv` ("Quantificar o valor agregado do RAG na resposta... endereça risco de eliminação 'só consome LLM via prompt'"), aberto antes de qualquer contato com a rubrica oficial do professor. A rubrica da linha IA confirmou a preocupação: ela lista explicitamente, em "Temas impedidos", soluções que "apenas consomem uma API de LLM por prompt, sem incorporar IA de fato". O RAG (recuperação por similaridade sobre embeddings, uma das abordagens aceitas em "Modelos Generativos") é a peça do projeto que sustenta a diferença — este documento mede se ela realmente funciona, e não apenas existe.

## Escopo desta medição

A base de conhecimento indexada hoje só está populada para um domínio: **`codigo_legado`**, com os 4 artefatos sintéticos em `backend/app/rag/fixtures/legacy_billing/` (`CreditLimitService.java`, `CustomerRepository.java`, `business-rules.md`, `schema.sql`) — um cenário fictício e autocontido de limite de crédito legado. Os domínios `regras_negocio`, `arquitetura_software` e `seguranca_informacao` ainda não têm base de conhecimento própria indexada, então a qualidade de recuperação deles não pôde ser medida por este método. Isso é uma limitação conhecida, não um resultado escondido.

## Metodologia

Duas medições complementares, ambas contra a API real da OpenRouter (sem mock):

**1. Qualidade da recuperação (quantitativa, automatizada)** — `backend/app/rag/evaluation.py` define 8 pares (pergunta, artefatos relevantes esperados), com o "esperado" definido manualmente a partir da leitura direta do conteúdo real dos 4 arquivos fixture — não é um gabarito gerado automaticamente. `backend/tests/test_rag_quality.py::test_retrieval_quality_against_ground_truth` ingere os 4 arquivos com embeddings reais, roda as 8 perguntas contra o `InMemoryVectorRetriever` (o mesmo retriever usado em produção) com `top_k=3` (igual ao `RAG_TOP_K` padrão), e calcula Precision@3, Recall@3 e Reciprocal Rank por pergunta — métricas padrão de recuperação de informação.

**2. Valor agregado na resposta final (qualitativa)** — comparação com/sem RAG habilitado, mesma solicitação técnica nos dois casos, com o texto da pergunta deliberadamente sem mencionar os fatos específicos do fixture (valor exato do limite, nome da coluna, nomes de classes) — qualquer fato específico que aparecer na resposta só pode ter vindo do contexto recuperado, não da pergunta.

## Resultado 1 — Qualidade da recuperação

```text
query                                                                  P@3   R@3   RR
Qual é o valor do limite de crédito hoje e em qual classe...          1.00   1.00   1.00
O campo SEGMENTO do cliente é considerado no cálculo...                1.00   0.50   1.00
Quais pontos do sistema dependem do limite de crédito atual...        1.00   1.00   1.00
Como o repositório calcula o total de pedidos em aberto...            0.50   1.00   1.00
Existe uma tabela no banco de dados dedicada ao limite...             0.00   0.00   0.00
Quais são os valores possíveis do campo SEGMENTO na tabela...         0.33   1.00   1.00
O CustomerRepository usa algum ORM para acessar o banco...            0.50   1.00   1.00
Qual método decide se um pedido pode ser aprovado...                  1.00   1.00   1.00

Mean P@3=0.667  Mean R@3=0.812  MRR=0.875  (n=8 queries)
```

**Leitura honesta:** em 7 das 8 perguntas o artefato certo foi recuperado na primeira posição (RR=1.0). A única falha completa (P@3=R@3=0.00) foi a pergunta sobre a tabela `SEGMENT_CREDIT_LIMIT` — o retriever não encontrou `schema.sql` relevante para essa pergunta, provavelmente porque a resposta certa ali é uma *ausência* (o comentário do arquivo diz que essa tabela não existe), e um comentário sobre "isso não existe" não fica semanticamente próximo, no espaço de embeddings, de uma pergunta afirmativa "existe uma tabela para X?". Isso ficou registrado como está, sem ajustar a pergunta ou o gabarito pra esconder o resultado.

O teste automatizado (`test_retrieval_quality_against_ground_truth`) trava a suíte se `MRR < 0.70` ou `Recall@3 médio < 0.65` — limiares fixados com margem real abaixo do que foi medido (0.875 e 0.812), deixando espaço para uma pergunta errar sem tratar a variação normal do embedding como regressão.

## Resultado 2 — Valor agregado na resposta final (com/sem RAG)

Três execuções reais capturadas, mesma pergunta ("como o limite de crédito do cliente é calculado hoje", sem revelar valores/nomes específicos):

**Com RAG (execução via suíte de testes, `test_rag_enabled_plan_reflects_retrieved_context`):**
```text
risks: ["Dependência de componentes que assumem limite fixo pode gerar
         inconsistências se a regra mudar sem atualização",
        "Ausência de testes automatizados que cubram cenário de limite
         variável por segmento"]
```
Os dois riscos batem com fatos que só existem no fixture (`business-rules.md` cita exatamente essa ausência de teste e essa dependência de componentes assumindo o valor fixo) — nenhum dos dois foi mencionado na pergunta.

**Com RAG (segunda execução, script manual):**
```text
summary: "Plano técnico para levantamento do cálculo atual do limite de
           crédito e identificação de seus dependentes."
risks: []
```
Resposta mais enxuta, sem listar riscos dessa vez — variação normal do modelo gratuito (já documentada em `docs/integrations/model-provider.md`), registrada aqui sem maquiagem.

**Sem RAG (mesma pergunta, RAG desabilitado):**
```text
required_skills: ["Análise de requisitos", "Documentação de processos",
                   "Entrevista com stakeholders", "Leitura de código/configuração"]
risks: ["Dependência de informações não centralizadas",
        "Possível desatualização de documentação"]
```

**Leitura honesta:** sem RAG, o modelo não tem como saber o valor do limite nem quem depende dele — e a resposta reflete isso: ele propõe atividades de descoberta genéricas ("entrevistar stakeholders", "ler código/configuração") em vez de citar qualquer fato concreto. Com RAG, quando a resposta não fica excessivamente enxuta, ela cita riscos específicos e verificáveis contra o fixture. O padrão é consistente nas duas execuções com RAG mesmo variando em verbosidade — nenhuma das duas "inventou" fatos fora do fixture, e nenhuma tentou adivinhar em vez de reconhecer a lacuna de informação.

## Teste automatizado

```text
pytest tests/test_rag_quality.py -v
2 passed
```

`ruff check app tests`: 0 findings. `mypy app`: 0 issues.

## Limitações deste registro

- Cobre só o domínio `codigo_legado` — os outros três domínios não têm base de conhecimento indexada ainda para serem medidos da mesma forma.
- A métrica de "valor agregado" (Resultado 2) é qualitativa e sujeita à variação natural do modelo gratuito entre execuções — não é uma métrica numérica reproduzível como o Resultado 1, e o teste automatizado reflete isso não fazendo asserção sobre o conteúdo textual da resposta, só sobre o mecanismo (a recuperação de fato ocorreu e alimentou a chamada).
- A falha na pergunta sobre a tabela inexistente (`schema.sql`) não foi corrigida nem descartada do gabarito — fica registrada como limitação real da abordagem de chunking/embedding atual, não como algo a esconder da rubrica.
- Este documento não substitui a medição formal dos KPIs do RFC (§5.5), registrada em `docs/validation/evidence/2026-08-m7-kpi-measurement.md`.
