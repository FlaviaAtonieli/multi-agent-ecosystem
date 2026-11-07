# Evidência: o conteúdo se repete mesmo quando o texto muda (07/11/2026)

**Pergunta:** a [medição de 05/11](2026-11-05-reproducibility.md) mostrou que, mesmo com `temperature=0` e `seed=42`, cada chamada devolve um texto diferente. As respostas diferentes dizem a mesma coisa?

## Como foi medido

- **Script:** [`backend/scripts/measure_repeatability.py`](../../../backend/scripts/measure_repeatability.py), no repositório, para qualquer pessoa repetir.
- **Entrada:** a mesma solicitação de 05/11 (limite de crédito por segmento), 5 vezes, com o provedor real do projeto, o mesmo prompt e o mesmo schema estrito.
- **Controle:** 2 respostas a outra pergunta técnica (logs sem correlação entre serviços), no mesmo formato. Isso dá a referência do que é "falar de outra coisa".
- **Comparação:** o resumo e os riscos de cada resposta viram um embedding. Mede-se a similaridade de cosseno entre as repetições e entre cada repetição e o controle.
- **Modelos:** só gratuitos, pelo proxy que recusa modelos pagos. Embeddings com `liquid/lfm-2.5-embedding-350m:free`.

## Resultado

| Modelo | Textos distintos | Entre repetições (média · mín) | Com o controle (média · máx) |
|---|---:|---:|---:|
| `dots-studio/dots-3-note-preview:free` | 5 de 5 | 0,842 · 0,747 | 0,286 · 0,346 |
| `nvidia/nemotron-3.5-super-vl:free` | 5 de 5 | 0,787 · 0,649 | 0,397 · 0,499 |

Nos dois modelos, a repetição menos parecida ainda ficou mais perto das outras repetições do que a resposta mais parecida ficou do controle. O texto muda, mas o assunto e os riscos apontados se mantêm.

A quantidade de riscos variou: de 4 a 8 no primeiro modelo e de 5 a 10 no segundo. Uma repetição pode trazer riscos que outra não traz.

## O que esta medição não mostra

- **Se o conteúdo está certo.** Respostas parecidas podem estar igualmente erradas. A correção depende da revisão humana e do Quality Gate.
- **O modelo de produção.** `openai/gpt-5-mini` é pago e não foi usado.
- **Uma régua de "equivalente".** A similaridade de embeddings separa bem "mesmo assunto" de "outro assunto", mas não diz se dois riscos são o mesmo risco. 5 repetições por modelo também é pouco.

## Conclusão para a linha de IA

O texto gerado não é replicável palavra por palavra, e o projeto não esconde isso. O conteúdo, porém, se repete de forma mensurável: as repetições têm similaridade média de 0,79 a 0,84 entre si (mínima 0,65), contra no máximo 0,50 com outro assunto. O que é determinístico (busca, métricas, Quality Gate, sugestão) continua sendo determinístico, e cada chamada ao modelo guarda modelo, parâmetros e hashes de entrada e saída.
