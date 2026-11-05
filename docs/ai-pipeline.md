# Pipeline de IA

Este documento descreve como a IA funciona no projeto, do dado até a resposta entregue ao usuário, e quais resultados foram medidos. A abordagem é um **modelo generativo com RAG** (*Retrieval-Augmented Generation*): antes de cada análise, o sistema busca trechos relevantes em uma base de conhecimento e os entrega ao modelo de linguagem como contexto.

A IA não é só um prompt enviado a uma API. As respostas passam por recuperação de conhecimento, contrato de saída validado, avaliação pelo Quality Gate e, quando necessário, revisão humana.

```text
Documentos da base        Solicitação do usuário
       |                           |
 1. Chunking e embeddings    2. Pré-processamento (mascaramento e limite)
       |                           |
       v                           v
 knowledge_chunks  <------  3. Recuperação (similaridade de cosseno, top 3)
                                   |
                            4. Modelo de linguagem (uma chamada por Agent Skill)
                                   |
                            5. Saída validada pelo contrato
                                   |
                            6. Quality Gate
                                   |
                     aprovada /            \ requer revisão
                  resposta entregue      revisão humana
```

## 1. Dados e indexação

**Fonte:** 22 documentos em [`backend/app/rag/fixtures/`](../backend/app/rag/fixtures/), como código, políticas, notas de arquitetura, auditorias e relatos de incidente. Eles descrevem um sistema legado de limite de crédito.

**Os dados são sintéticos.** Todos os documentos foram escritos para este projeto e giram em torno de um sistema fictício. A base não usa um dataset pronto.

**Por que dados sintéticos:**

- Código e documentação internos de uma empresa costumam ser confidenciais e podem conter dados pessoais, o que traria risco de privacidade e de LGPD para uma Prova de Conceito.
- Com um sistema conhecido, é possível escrever um gabarito do que deveria ser recuperado e medir o resultado.
- Os mesmos documentos podem ser usados de novo, o que permite repetir as medições.

**Limitação:** os resultados mostram o comportamento do pipeline nesses documentos, não em um ambiente corporativo real. Na medição de setembro, os documentos e o gabarito de três áreas foram escritos juntos, o que pode favorecer o resultado.

**Indexação** ([`ingestion.py`](../backend/app/rag/ingestion.py) e [`seed_knowledge_base.py`](../backend/app/db/seed_knowledge_base.py)):

| Etapa | Implementação | Justificativa |
|---|---|---|
| Chunking | Janelas de 800 caracteres, com 100 de sobreposição | Simples e suficiente para documentos pequenos. A sobreposição reduz o corte de uma informação ao meio |
| Embeddings | `openai/text-embedding-3-small`, pela OpenRouter | Modelo pronto e de baixo custo. O projeto não treina modelo próprio |
| Armazenamento | Tabela `knowledge_chunks` no PostgreSQL | Dispensa um banco vetorial no volume da Prova de Conceito |

## 2. Pré-processamento da solicitação

Antes de qualquer chamada externa, [`llm/security.py`](../backend/app/llm/security.py) mascara tokens, chaves, senhas e e-mails e aplica o limite de tamanho. O banco guarda hashes SHA-256 da entrada e da saída, e não o conteúdo integral, por padrão.

## 3. Recuperação

[`retriever.py`](../backend/app/rag/retriever.py) gera o embedding da consulta (problema, objetivo, contexto e nome da área), calcula a similaridade de cosseno com todos os trechos e devolve os 3 melhores.

- **Sem filtro por área:** todos os trechos competem no mesmo ranking, e o nome da área só influencia o texto da consulta.
- **Sem índice vetorial:** a busca percorre todos os trechos em memória. Funciona no volume atual, mas não escala para uma base grande.

## 4. Modelo de linguagem

Cada Agent Skill é chamada por meio do protocolo MCP e faz uma chamada à OpenRouter, com as instruções da skill, os trechos recuperados e a solicitação. O modelo padrão é `openai/gpt-5-mini`, escolhido depois que o modelo gratuito anterior saiu do catálogo. O usuário escolhe outro entre os permitidos em `LLM_ALLOWED_MODELS`.

Só as skills ativas do **clã escolhido** são chamadas, o que evita gastar tokens com skills fora do assunto.

Quando a solicitação pede um arquivo, código ou projeto, o modelo também devolve `generated_files`. Os nomes e o conteúdo são tratados como não confiáveis: caminhos que poderiam sair da pasta do projeto são recusados, e nada é executado. Depois de gerados, mostrar, baixar e compactar os arquivos não chama o modelo.

## 5. Pós-processamento

- **Contrato de saída:** a resposta precisa seguir um JSON Schema estrito e é validada com Pydantic.
- **Nível de confiança:** cada skill define um nível (`ALTO`, `MEDIO` ou `BAIXO`) a partir da evidência disponível. Sem nenhum trecho recuperado, por exemplo, a confiança é `BAIXO`.
- **Quality Gate** ([`quality_gate/service.py`](../backend/app/quality_gate/service.py)): regras explícitas, sem um segundo modelo julgando. Reprova com confiança baixa ou divergência entre skills da mesma área, e confiança média exige revisão humana.
- **Revisão humana:** quando o Quality Gate não aprova, a pessoa aprova ou rejeita com justificativa. A PoC só faz recomendações e não altera nenhum sistema.
- **Rastreabilidade:** cada etapa vira um evento na linha do tempo, ligado ao `Trace ID`.

## 6. Validação

A qualidade da recuperação foi medida com um gabarito manual, usando Precision@3, Recall@3 e MRR ([`evaluation.py`](../backend/app/rag/evaluation.py)). Este tipo de pipeline não treina modelo, então k-fold e holdout não se aplicam: a técnica adequada é comparar o que foi recuperado com o gabarito.

| Área | Perguntas | Precision@3 | Recall@3 | MRR |
|---|---:|---:|---:|---:|
| Código Legado | 8 | 0,479 | 0,750 | 0,875 |
| Regras de Negócio | 5 | 0,467 | 1,000 | 1,000 |
| Arquitetura de Software | 5 | 0,567 | 0,900 | 0,900 |
| Segurança da Informação | 5 | 0,767 | 1,000 | 1,000 |

Fonte: [medição de 21/09/2026](validation/evidence/2026-09-rag-multi-domain-quality-validation.md). `test_retrieval_quality_against_ground_truth` falha se a qualidade cair abaixo dos limites fixados.

**O que ainda não foi medido:**

- As outras 6 áreas oficiais.
- A qualidade da resposta final do modelo: as medições cobrem a recuperação.
- Os KPIs da RFC com o código e o modelo atuais. A [rodada de agosto](validation/evidence/2026-08-m7-kpi-measurement.md) usou um modelo gratuito e execução em sequência.

## Motor de sugestão de skills

Antes de registrar a solicitação, a pessoa pode verificar se alguma skill fora do clã ajudaria. O texto da solicitação, mascarado, e o de cada skill ativa (nome, área, objetivo e capacidades) viram embeddings, comparados por similaridade de cosseno. O vetor de cada skill fica guardado até o texto dela mudar. O motor só sugere, e a pessoa decide.

**Por que não uma CNN ou outro modelo treinado:** não há exemplos rotulados de "solicitação e skill certa", e um dataset pronto como dados da solução reprova na linha de IA. A similaridade dispensa treino e pode ser medida com gabarito.

**A qualidade ainda não foi medida com embeddings reais.** `tests/test_skill_suggestion_quality.py` mede Precision@3, Recall@3 e MRR em 20 perguntas e mostra as notas de 3 perguntas fora do assunto. O limite `SKILL_SUGGESTION_MIN_SCORE` (0,35) é um valor inicial, até essa calibração.

## Reprodutibilidade

| Etapa | Repetir dá o mesmo resultado? |
|---|---|
| Chunking e ranking dos trechos | Sim, com os mesmos embeddings |
| Métricas de recuperação | Sim, desde que o provedor mantenha o modelo de embeddings: mesmo gabarito e mesmos documentos |
| Quality Gate | Sim, para as mesmas respostas das skills |
| Sugestão de skills | Sim, com os mesmos embeddings e o mesmo limite |
| Texto gerado pelo modelo | **Não necessariamente.** Modelos de linguagem variam, e o projeto não fixa `temperature` nem `seed` |

Para repetir as medições, rode os testes marcados com `llm` (ver README). Eles exigem uma `OPENROUTER_API_KEY` real e geram custo.

## Ética e privacidade

- Dados pessoais são mascarados antes de sair do sistema, e o conteúdo integral não é guardado por padrão.
- A base de conhecimento não contém dados de pessoas reais.
- O usuário pode excluir a própria conta.
- O modelo não decide sozinho: a responsabilidade pela decisão continua humana (RFC, seção 6.5).

## Limitações conhecidas

- O chunking não considera a estrutura do texto, então um trecho pode cortar uma função ou um parágrafo.
- A base de conhecimento é compartilhada entre as áreas. Uma skill de outra área, como contabilidade, roda, mas só tem os próprios anexos da solicitação como evidência da área.
- Os anexos só aceitam texto puro, sem PDF ou DOCX.
