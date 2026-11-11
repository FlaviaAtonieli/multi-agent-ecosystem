# Apresentação para a banca

Material de preparação: o roteiro da demonstração, o texto do pôster e as perguntas para ensaiar a prova de autoria. Os números vêm das evidências em [docs/validation/evidence/](../validation/evidence/). Se uma medição for refeita, atualize aqui também.

## Roteiro da demonstração (10 minutos)

Antes de começar: ligar o App Service e o banco no Azure, entrar uma vez para esquentar o backend e deixar aberta uma orquestração já concluída, como reserva caso o modelo demore.

| Tempo | O que mostrar | O que dizer |
|---|---|---|
| 0:00 | Tela inicial e login | O problema: especialistas de áreas diferentes respondem cada um por si, e ninguém consolida. A proposta é coordenar agentes especialistas com rastreabilidade. |
| 1:00 | Catálogo de Agent Skills | Cada skill é um manifesto validado (RF03). As 10 oficiais e uma criada pelo formulário. |
| 2:00 | Clãs | O clã define quem responde. Mostrar o motor de sugestão indicando uma skill de fora do clã. |
| 3:00 | Nova solicitação com "TESTE TESTE..." | A barreira de contexto recusa uma solicitação sem conteúdo e diz o que falta. |
| 4:00 | Nova solicitação real, executar | A execução roda em segundo plano. A linha do tempo mostra cada etapa com o `Trace ID`. |
| 5:30 | Resposta final | Resumo, material desenvolvido (arquivos e ZIP) e a resposta de cada agente, fechada por padrão. |
| 7:00 | Quality Gate e revisão humana | Por que esta resposta foi para revisão. Aprovar ou rejeitar com justificativa. |
| 8:00 | Auditoria e Grafana | Cada evento fica registrado. As métricas mostram execuções, vereditos e tempo. |
| 9:00 | Limites | RNF07 não atingido (71 s contra 10 s, dominado pelo modelo). O texto do modelo muda a cada chamada, mas o conteúdo se repete. |

## Texto do pôster

**Título.** Flav.IA: coordenação de agentes especialistas em ambientes corporativos

**Problema.** Uma dúvida técnica real cruza várias áreas (código legado, regras de negócio, segurança). Cada especialista responde só pela sua, e a decisão fica sem uma visão consolidada nem registro de como foi tomada.

**Proposta.** Uma plataforma em que cada especialista é uma Agent Skill isolada, chamada por MCP. Um orquestrador escolhe as skills do clã, junta as respostas, passa por um Quality Gate e, quando precisa, por revisão humana. Tudo fica ligado a um `Trace ID`.

**Arquitetura.** React no Azure Static Web Apps, FastAPI no App Service, PostgreSQL, OpenRouter como gateway de modelos, RAG com base de conhecimento por área, Prometheus e Grafana. Diagrama em [overview.md](../architecture/overview.md).

**Resultados.**

- Busca (RAG) medida com gabarito nas 10 áreas. Nas 4 primeiras, com o modelo pago: MRR de 0,875 a 1,000.
- Limite do motor de sugestão escolhido por k-fold: acurácia balanceada de 0,958 nas partes que não participaram da escolha (modelo gratuito).
- Repetição: o texto muda a cada chamada, mas as repetições têm similaridade média de 0,79 a 0,84 entre si, contra no máximo 0,50 com outra pergunta.
- Caso da batalha naval: com os requisitos das outras skills, o mesmo modelo passou em 17 de 17 verificações do jogo; sem eles, em 11.
- 420 testes no backend (90% de cobertura) e 153 no frontend, com o código quebrado de propósito para conferir que os testes acusam.

**Limites.** Tempo de resposta acima da meta (o modelo domina). Modelos gratuitos geram código pior. As regras do Quality Gate só pegam o que foi previsto.

**Equipe e orientação.** Preencher com os nomes, a orientação e o QR code do repositório.

## Perguntas para ensaiar a prova de autoria

Cada pessoa da equipe deve conseguir responder sem consultar o código. Entre parênteses, onde está a resposta.

1. Por que MCP por stdio, e não chamar as skills como funções? ([decisões, 1](../architecture/decisions.md#1-cada-agent-skill-é-um-servidor-mcp-de-verdade))
2. O que acontece se duas pessoas clicarem em "Executar" ao mesmo tempo? (`claim_request_for_execution` em [orchestration_runner.py](../../backend/app/services/orchestration_runner.py))
3. Por que o Quality Gate não usa um LLM como juiz, e o que ele deixa passar? ([decisões, 5](../architecture/decisions.md#5-quality-gate-por-regras-sem-um-llm-como-juiz))
4. Por que a busca não usa pgvector? Até quantos documentos isso aguenta? ([decisões, 3](../architecture/decisions.md#3-rag-com-busca-linear-no-banco-sem-pgvector))
5. Como foi escolhido o limite do motor de sugestão, e por que ele vale só para um modelo? ([medição](../validation/evidence/2026-11-07-suggestion-threshold-kfold.md))
6. O resultado é replicável? O que é e o que não é? ([pipeline, Reprodutibilidade](../architecture/ai-pipeline.md#reprodutibilidade))
7. Por que as skills que escrevem código rodam depois das outras? O que piorou na primeira versão? ([decisões, 6](../architecture/decisions.md#6-quem-escreve-código-roda-depois-dos-outros))
8. Como uma pessoa sem conta de administrador é impedida de editar a skill de outra? ([decisões, 7](../architecture/decisions.md#7-acesso-por-propriedade-visibilidade-e-cota-sem-papéis) e [SECURITY.md](../../SECURITY.md))
9. O que impede um arquivo gerado pelo modelo de escapar da pasta ao extrair o ZIP? ([artifact_service.py](../../backend/app/services/artifact_service.py))
10. Por que a orquestração roda em segundo plano, e o que acontece se o servidor reiniciar no meio? ([decisões, 8](../architecture/decisions.md#8-a-orquestração-roda-em-segundo-plano))
11. Onde o assistente de IA ajudou no desenvolvimento, e como vocês conferiram o que ele fez? ([README, Uso de IA](../../README.md#uso-de-ia-no-desenvolvimento))
12. Qual requisito do RFC não foi atingido, e por quê? ([RFC, Apêndice J](../rfc/))

Sugestão de ensaio: uma pessoa sorteia 4 perguntas para outra, com 2 minutos por resposta, e anota onde a resposta ficou vaga.
