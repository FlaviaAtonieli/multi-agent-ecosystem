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

**Fonte:** 22 documentos em [`backend/app/rag/fixtures/`](../../backend/app/rag/fixtures), como código, políticas, notas de arquitetura, auditorias e relatos de incidente. Eles descrevem um sistema legado de limite de crédito.

**Os dados são sintéticos.** Todos os documentos foram escritos para este projeto e giram em torno de um sistema fictício. A base não usa um dataset pronto.

**Por que dados sintéticos:**

- Código e documentação internos de uma empresa costumam ser confidenciais e podem conter dados pessoais, o que traria risco de privacidade e de LGPD para uma Prova de Conceito.
- Com um sistema conhecido, é possível escrever um gabarito do que deveria ser recuperado e medir o resultado.
- Os mesmos documentos podem ser usados de novo, o que permite repetir as medições.

**Limitação:** os resultados mostram o comportamento do pipeline nesses documentos, não em um ambiente corporativo real. Na medição de setembro, os documentos e o gabarito de três áreas foram escritos juntos, o que pode favorecer o resultado.

**Indexação** ([`ingestion.py`](../../backend/app/rag/ingestion.py) e [`seed_knowledge_base.py`](../../backend/app/db/seed_knowledge_base.py)):

| Etapa | Implementação | Justificativa |
|---|---|---|
| Chunking | Janelas de 800 caracteres, com 100 de sobreposição | Simples e suficiente para documentos pequenos. A sobreposição reduz o corte de uma informação ao meio |
| Embeddings | `openai/text-embedding-3-small`, pela OpenRouter | Modelo pronto e de baixo custo. O projeto não treina modelo próprio |
| Armazenamento | Tabela `knowledge_chunks` no PostgreSQL | Dispensa um banco vetorial no volume da Prova de Conceito |

## 2. Pré-processamento da solicitação

Antes de qualquer chamada externa, [`llm/security.py`](../../backend/app/llm/security.py) mascara tokens, chaves, senhas e e-mails e aplica o limite de tamanho. O banco guarda hashes SHA-256 da entrada e da saída, e não o conteúdo integral, por padrão.

## 3. Recuperação

[`retriever.py`](../../backend/app/rag/retriever.py) gera o embedding da consulta (problema, objetivo, contexto e nome da área), calcula a similaridade de cosseno com todos os trechos e devolve os 3 melhores.

- **Sem filtro por área:** todos os trechos competem no mesmo ranking, e o nome da área só influencia o texto da consulta.
- **Sem índice vetorial:** a busca percorre todos os trechos em memória. Funciona no volume atual, mas não escala para uma base grande.

## 4. Modelo de linguagem

Cada Agent Skill é chamada por meio do protocolo MCP e faz uma chamada à OpenRouter, com as instruções da skill, os trechos recuperados e a solicitação. O modelo padrão é `openai/gpt-5-mini`, escolhido depois que o modelo gratuito anterior saiu do catálogo. O usuário escolhe outro entre os permitidos em `LLM_ALLOWED_MODELS`.

Só as skills ativas do **comitê escolhido** são chamadas, o que evita gastar tokens com skills fora do assunto.

Quando a solicitação pede um arquivo, código ou projeto, o modelo também devolve `generated_files`. Os nomes e o conteúdo são tratados como não confiáveis: caminhos que poderiam sair da pasta do projeto são recusados, e nada é executado. Depois de gerados, mostrar, baixar e compactar os arquivos não chama o modelo.

## 5. Pós-processamento

- **Contrato de saída:** a resposta precisa seguir um JSON Schema estrito e é validada com Pydantic.
- **Nível de confiança:** cada skill define um nível (`ALTO`, `MEDIO` ou `BAIXO`) a partir da evidência disponível. Sem nenhum trecho recuperado, por exemplo, a confiança é `BAIXO`.
- **Quality Gate** ([`quality_gate/service.py`](../../backend/app/quality_gate/service.py)): regras explícitas, sem um segundo modelo julgando. Reprova com confiança baixa ou divergência entre skills da mesma área, e confiança média exige revisão humana.
- **Revisão humana:** quando o Quality Gate não aprova, a pessoa aprova ou rejeita com justificativa. A PoC só faz recomendações e não altera nenhum sistema.
- **Rastreabilidade:** cada etapa vira um evento na linha do tempo, ligado ao `Trace ID`.

## 6. Validação

A qualidade da recuperação foi medida com um gabarito manual, usando Precision@3, Recall@3 e MRR ([`evaluation.py`](../../backend/app/rag/evaluation.py)). Este tipo de pipeline não treina modelo, então k-fold e holdout não se aplicam à recuperação: a técnica adequada é comparar o que foi recuperado com o gabarito. O único número ajustado com dados, o limite do motor de sugestão, foi calibrado por k-fold (ver adiante).

| Área | Perguntas | Precision@3 | Recall@3 | MRR |
|---|---:|---:|---:|---:|
| Código Legado | 8 | 0,479 | 0,750 | 0,875 |
| Regras de Negócio | 5 | 0,467 | 1,000 | 1,000 |
| Arquitetura de Software | 5 | 0,567 | 0,900 | 0,900 |
| Segurança da Informação | 5 | 0,767 | 1,000 | 1,000 |

Fonte: [medição de 21/09/2026](../validation/evidence/2026-09-rag-multi-domain-quality-validation.md), com o modelo de embeddings pago. `test_retrieval_quality_against_ground_truth` falha se a qualidade cair abaixo dos limites fixados.

As outras 6 áreas ganharam gabarito em 06/11/2026 e foram medidas, junto com as 4 primeiras, só com um modelo de embeddings gratuito ([medição](../validation/evidence/2026-11-06-rag-ten-domains.md)):

| Área | Perguntas | Precision@3 | Recall@3 | MRR |
|---|---:|---:|---:|---:|
| Qualidade e Testes | 5 | 0,267 | 0,400 | 0,367 |
| Observabilidade e Monitoramento | 5 | 0,267 | 0,600 | 0,600 |
| Performance e Escalabilidade | 5 | 0,300 | 0,800 | 0,700 |
| Dados e Privacidade (LGPD) | 5 | 0,533 | 1,000 | 1,000 |
| Infraestrutura e DevOps | 5 | 0,667 | 1,000 | 1,000 |
| APIs e Integrações | 5 | 0,400 | 1,000 | 0,667 |

Com o modelo gratuito, Código Legado cai de MRR 0,875 para 0,500. As áreas mais fracas são as que dividem assunto com outras (o `RiskBatchJob` aparece em testes, observabilidade e performance).

### Limite do motor de sugestão

`SKILL_SUGGESTION_MIN_SCORE` foi escolhido por k-fold estratificado (k=4): 20 perguntas do assunto e 12 fora dele. Em cada rodada, o limite é escolhido em 3 partes e medido na quarta ([`calibration.py`](../../backend/app/rag/calibration.py)). Com o modelo de embeddings gratuito, a acurácia balanceada média nas partes de fora foi 0,958, com limites entre 0,112 e 0,118 ([medição](../validation/evidence/2026-11-07-suggestion-threshold-kfold.md)). O limite depende do modelo: o 0,35 configurado precisa ser conferido com o modelo pago de produção.

### Avaliação humana das respostas

Cada resposta de agente pode ser marcada como útil ou não útil. Não útil exige um motivo: incorreta, incompleta, fora do assunto ou sem evidência ([`feedback_service.py`](../../backend/app/services/feedback_service.py)). A avaliação só registra: não muda a resposta nem a decisão do Quality Gate.

A métrica `agenthub_agent_response_feedback` cruza a avaliação com a área, a confiança que a skill declarou e o veredito do Quality Gate. Com isso dá para ver:

- a **taxa de aprovação humana** por área;
- se a confiança declarada significa algo: respostas de confiança alta deveriam ser mais aprovadas que as de confiança baixa;
- quantas respostas **passaram pelo Quality Gate e foram marcadas como não úteis**, que é a medida do que as regras deixam passar.

É a percepção de quem usou, não uma acurácia contra gabarito. Quem avalia é quem abriu a solicitação, e as pessoas tendem a avaliar mais quando gostam muito ou desgostam muito. Por isso cada taxa aparece junto com o número de avaliações. As avaliações também servem de rótulo para trabalhos futuros, como um classificador para a sugestão de skills ou um reordenador dos trechos do RAG.

**O que ainda não foi medido:**

- As 6 áreas novas com o modelo de embeddings pago, usado em produção.
- O limite do motor de sugestão com o modelo de embeddings pago.
- A qualidade da resposta final com volume: a avaliação humana existe, mas até agora só a equipe avaliou.
- Os KPIs da RFC com o código e o modelo atuais. A [rodada de agosto](../validation/evidence/2026-08-m7-kpi-measurement.md) usou um modelo gratuito e execução em sequência.

## Cache

- **Embeddings:** o mesmo texto com o mesmo modelo não gera nova chamada. O cache fica no banco (`embedding_cache`), porque cada skill roda em um processo próprio, e guarda só o hash do texto.
- **Vetores das skills:** ficam guardados até o texto da skill ou o modelo mudar.
- **Site:** os arquivos de `/assets`, cujo nome muda a cada build, podem ficar guardados por 1 ano. O `index.html` é sempre revalidado.

## Motor de sugestão de skills

Antes de registrar a solicitação, a pessoa pode verificar se alguma skill fora do comitê ajudaria. O texto da solicitação, mascarado, e o de cada skill ativa (nome, área, objetivo e capacidades) viram embeddings, comparados por similaridade de cosseno. O vetor de cada skill fica guardado até o texto dela mudar. O motor só sugere, e a pessoa decide.

**Por que não uma CNN ou outro modelo treinado:** não há exemplos rotulados de "solicitação e skill certa", e um dataset pronto como dados da solução reprova na linha de IA. A similaridade dispensa treino e pode ser medida com gabarito.

**Medição de 05/11/2026, com embeddings gratuitos:** Recall@3 de 1,00 e MRR de 0,91 em 20 perguntas ([evidência](../validation/evidence/2026-11-05-real-llm-free-models.md)). O ranking funciona, mas o limite `SKILL_SUGGESTION_MIN_SCORE` (0,35) não: com esse modelo, as notas das perguntas do assunto e das de fora se sobrepõem. O limite precisa ser calibrado com o modelo de embeddings de produção.

## Reprodutibilidade

| Etapa | Repetir dá o mesmo resultado? |
|---|---|
| Chunking e ranking dos trechos | Sim, com os mesmos embeddings |
| Métricas de recuperação | Sim, desde que o provedor mantenha o modelo de embeddings: mesmo gabarito e mesmos documentos |
| Quality Gate | Sim, para as mesmas respostas das skills |
| Sugestão de skills | Sim, com os mesmos embeddings e o mesmo limite |
| Texto gerado pelo modelo | **Não.** O projeto envia `temperature=0` e `seed=42` e guarda os valores em cada chamada (`llm_invocations`), mas, em 3 modelos gratuitos, 4 repetições deram 4 respostas diferentes ([medição de 05/11/2026](../validation/evidence/2026-11-05-reproducibility.md)) |
| Conteúdo gerado pelo modelo | **Em boa parte.** As repetições têm similaridade média de 0,79 a 0,84 entre si, contra no máximo 0,50 com a resposta a outra pergunta, em 2 modelos gratuitos ([medição de 07/11/2026](../validation/evidence/2026-11-07-content-repeatability.md), [script](../../backend/scripts/measure_repeatability.py)) |

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
