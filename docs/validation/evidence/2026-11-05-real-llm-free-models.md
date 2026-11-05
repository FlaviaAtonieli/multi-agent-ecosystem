# Evidência: testes com a IA real, em modelos gratuitos

**Data:** 05/11/2026
**Escopo:** os 27 testes marcados com `llm`, que chamam a OpenRouter de verdade, mais a medição do motor de sugestão.

## Como foi feito

- **Somente modelos gratuitos**, por decisão da autora. Um proxy local recusava qualquer modelo pago, e ele recusou de fato uma chamada a `openai/gpt-5-mini` feita por um teste.
- **Chat:** `dots-studio/dots-3-note-preview:free`, o modelo que a suíte fixa em `REAL_LLM_MODEL`.
- **Embeddings:** primeiro `nvidia/nemotron-3.5-embed-1b:free`. Os testes que falharam por instabilidade dele rodaram de novo com `liquid/lfm-2.5-embedding-350m:free`.
- **Parâmetros:** `temperature=0` e `seed=42`.
- **Custo registrado pela OpenRouter:** zero em todas as chamadas.

## Resultado dos 27 testes

**25 de 27 passaram** no total, com 23 na primeira rodada.

| Situação | Testes | Causa |
|---|---|---|
| Passaram na primeira rodada | 23 | Orquestração, MCP por stdio, perguntas, revisão humana, cota e RAG de ponta a ponta |
| Passaram com outro modelo de embeddings | 2 | O primeiro modelo respondeu `service inference failed` (502) em 12 chamadas, uma falha do provedor |
| Passou depois de corrigir o teste | 1 | O motor de sugestão: a medição fazia mais consultas que o limite de 20 por minuto da API, e o teste foi ajustado |
| **Abaixo do limite fixado** | 1 | `test_retrieval_quality_against_ground_truth`: qualidade da busca com o modelo gratuito, ver abaixo |

## Busca do RAG: modelo pago e gratuito

Mesmo gabarito de 8 perguntas do domínio Código Legado.

| Modelo de embeddings | Precision@3 | Recall@3 | MRR | Fonte |
|---|---:|---:|---:|---|
| `openai/text-embedding-3-small` (pago) | 0,479 | 0,750 | 0,875 | [21/09/2026](2026-09-rag-multi-domain-quality-validation.md), com 4 domínios indexados |
| `liquid/lfm-2.5-embedding-350m:free` | 0,333 | 0,531 | 0,500 | esta medição, com 1 domínio indexado |

O modelo gratuito, menor, recupera pior: o teste exige MRR de pelo menos 0,70 e ficou em 0,50. **Com modelos gratuitos, a qualidade do RAG cai.** As duas medições não são idênticas: a de setembro tinha 4 domínios competindo no mesmo ranking. Ainda assim, mostram a direção.

## Motor de sugestão

20 perguntas com a área esperada, sem citar o nome da área, mais 3 fora do assunto. Embeddings `liquid/lfm-2.5-embedding-350m:free`.

| Métrica | Valor |
|---|---:|
| Recall@3 | **1,00**: a área certa ficou entre as 3 primeiras em todas |
| MRR | **0,91**: em primeiro lugar em 17 de 20 |
| Precision@3 | 0,33: o máximo possível com uma área certa e 3 sugestões |
| Nota da melhor sugestão, nas perguntas do assunto | de 0,135 a 0,570 |
| Nota da melhor sugestão, nas perguntas fora do assunto | 0,163, 0,047 e 0,074 |

Erros de ordem: "desconto progressivo por segmento" e "política de aprovação de crédito" foram para outras áreas antes de Regras de Negócio, e "métricas e painéis" foi para APIs antes de Observabilidade.

**Limite de similaridade:** com este modelo, nenhum valor separa os dois grupos. A menor nota de uma pergunta do assunto, 0,135, fica abaixo da maior de uma pergunta fora do assunto, 0,163. O valor atual, 0,35, deixaria 11 das 20 perguntas sem sugestão. **Esta calibração vale só para o modelo usado:** em produção, os embeddings são de `openai/text-embedding-3-small`, e as notas mudam de escala com o modelo.

## O que ainda falta

- Repetir a busca do RAG com as 10 áreas indexadas, nos dois modelos, e separar perguntas de ajuste e de teste.
- Calibrar o limite do motor com o modelo de embeddings de produção, ou trocar produção para um modelo gratuito e reindexar a base, aceitando a perda de qualidade medida acima.
- Medir a qualidade da resposta final do modelo, e não só a busca.
