# Qualidade do RAG nas 10 áreas, 06/11/2026

Até aqui, a recuperação de trechos só tinha gabarito em 4 das 10 áreas oficiais. Esta medição cria o gabarito das outras 6 e mede as 10 juntas.

## Como foi feito

- **Gabarito:** foram escritas 5 perguntas para cada uma das 6 áreas novas, 30 no total, todas a partir do conteúdo real dos documentos de `backend/app/rag/fixtures/`. Cada pergunta lista todos os documentos que a respondem. As perguntas usam o jeito de falar de quem pergunta, e não as palavras dos documentos: "a rede de segurança antes de mudar a regra", e não "teste de regressão". O gabarito está em `backend/app/rag/evaluation.py`.
- **Base:** os 10 conjuntos de documentos foram indexados juntos, como em produção. Por isso os documentos das outras áreas competem no ranking.
- **Modelo de embeddings:** `liquid/lfm-2.5-embedding-350m:free`, gratuito. O modelo pago, padrão em produção, não foi usado, para a medição custar zero.
- **Métricas:** Precision@3, Recall@3 e MRR, contadas por documento e não por trecho.
- **Reprodução:** `pytest -m llm tests/test_rag_quality.py`, com `EMBEDDING_MODEL` apontando para o mesmo modelo.

## Resultado

| Área | Perguntas | P@3 | R@3 | MRR |
|---|---|---|---|---|
| Código Legado | 8 | 0,333 | 0,531 | 0,500 |
| Regras de Negócio | 5 | 0,500 | 1,000 | 1,000 |
| Arquitetura de Software | 5 | 0,467 | 0,900 | 0,767 |
| Segurança da Informação | 5 | 0,533 | 1,000 | 0,900 |
| **Qualidade e Testes** | 5 | 0,267 | 0,400 | 0,367 |
| **Observabilidade e Monitoramento** | 5 | 0,267 | 0,600 | 0,600 |
| **Performance e Escalabilidade** | 5 | 0,300 | 0,800 | 0,700 |
| **Dados e Privacidade (LGPD)** | 5 | 0,533 | 1,000 | 1,000 |
| **Infraestrutura e DevOps** | 5 | 0,667 | 1,000 | 1,000 |
| **APIs e Integrações** | 5 | 0,400 | 1,000 | 0,667 |

As 6 áreas em negrito foram medidas pela primeira vez. As 4 primeiras repetem a medição de 05/11/2026, feita com o mesmo modelo gratuito. Código Legado dá MRR de 0,500 nas duas, então a montagem é a mesma.

A Precision@3 é baixa em todas as áreas por construção: cada pergunta tem 1 ou 2 documentos certos entre 3 posições.

## O que não foi encontrado

Em 7 das 53 perguntas, nenhum documento certo apareceu entre os 3 primeiros:

- **Qualidade e Testes:**
  - "O job noturno de risco e o relatório financeiro têm testes próprios?"
  - "Que rede de segurança criar antes de mudar a regra de cálculo do limite?"
- **Observabilidade e Monitoramento:**
  - "Os logs da aprovação de pedidos permitem correlacionar as linhas de uma mesma requisição?"
  - "Que instrumentação mínima foi recomendada antes de alterar a regra de negócio?"
- **Performance e Escalabilidade:**
  - "Por que o job de risco fica mais lento a cada mês?"
- **Código Legado:** 2 perguntas, as mesmas que já falhavam em 05/11.

O padrão é o mesmo nos casos: perguntas sobre o `RiskBatchJob` e sobre a regra de cálculo aparecem em documentos de várias áreas, que citam uns aos outros. O modelo pequeno puxa o documento de outra área que menciona os mesmos nomes.

As perguntas não foram reescritas para melhorar o número. Isso mediria o gabarito, não a busca.

## Pisos de regressão

`tests/test_rag_quality.py` passa a cobrar as 10 áreas. Nas 6 novas, o piso fica cerca de uma pergunta (0,20) abaixo do valor medido com o modelo gratuito. Nas 4 áreas medidas com os dois modelos, o pago teve resultado igual ou melhor, então esses pisos funcionam como limite inferior também para ele.

## O que continua sem medição

- As 6 áreas novas com o modelo pago de produção. O custo seria de centavos, mas é preciso autorizar.
- A qualidade da resposta final do modelo. Esta medição cobre só a busca.
