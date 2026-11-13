# Decisões de arquitetura

Registro curto das decisões que mais moldam o sistema. Cada uma diz o contexto, o que foi decidido e o que isso custa. Os [princípios](principles.md) dizem as regras gerais; aqui ficam as escolhas concretas.

## 1. Cada Agent Skill é um servidor MCP de verdade

**Contexto.** O RFC pede agentes isolados, que se descobrem por contrato.

**Decisão.** O orquestrador é um cliente MCP. Cada chamada sobe um processo do servidor da skill e conversa por JSON-RPC sobre stdio ([`mcp_client.py`](../../backend/app/agent_catalog/mcp_client.py)). Antes de chamar, o cliente lista as ferramentas do servidor e confere que `executar` existe. O servidor abre a própria sessão de banco e busca de novo os dados pelos ids recebidos.

**Custo.** Um processo por chamada gasta memória e tempo de partida. Por isso `ORCHESTRATION_MAX_PARALLEL_SKILLS` limita quantas rodam juntas. Nos testes, o transporte em memória usa o mesmo servidor sem subir processo.

## 2. Um executor e um servidor para todas as skills

**Contexto.** Havia um executor e um servidor por área oficial, e os cinco eram de 86% a 90% iguais.

**Decisão.** Um só [`SkillExecutor`](../../backend/app/agent_catalog/tool_interface.py) e um só [`skill_server.py`](../../backend/app/agent_catalog/mcp_servers/skill_server.py). O que muda de uma área para outra são as instruções da skill e as frases sobre a evidência, que ficam em dados.

**Custo.** Uma skill que precisasse de lógica própria, e não só de outro texto, exigiria voltar a ter um executor separado.

## 3. RAG com busca linear no banco, sem pgvector

**Contexto.** A base tem dezenas a centenas de trechos, e os testes rodam em SQLite.

**Decisão.** Os embeddings ficam numa coluna JSON e a busca calcula a similaridade de cosseno em Python ([`retriever.py`](../../backend/app/rag/retriever.py)). A qualidade é medida contra um gabarito ([Pipeline de IA](ai-pipeline.md)).

**Custo.** Não escala para milhares de documentos. Nesse ponto, o caminho é pgvector ou um banco vetorial, atrás da mesma interface `Retriever`.

## 4. O comitê define quem responde

**Contexto.** Chamar todas as skills a cada solicitação gasta tokens com áreas fora do assunto.

**Decisão.** A solicitação escolhe um comitê, e só as skills ativas dele respondem. O [motor de sugestão](../../backend/app/services/skill_suggestion_service.py) indica skills de fora que podem ajudar, por embeddings, e a pessoa decide se as adiciona.

**Nome.** Até novembro de 2026 o comitê se chamava clã. A troca valeu para as telas e os documentos; no código, no banco e na API o nome continua `clan`, e o endereço antigo `/clans` leva para `/comites`.

**Custo.** Um comitê mal montado dá uma resposta pobre. A sugestão ajuda, mas não corrige sozinha.

## 5. Quality Gate por regras, sem um LLM como juiz

**Contexto.** Um segundo modelo avaliando o primeiro seria caro, difícil de testar e de explicar.

**Decisão.** O [Quality Gate](../../backend/app/quality_gate/service.py) aplica regras explícitas: confiança baixa, respostas que divergem entre si, arquivos pedidos e não entregues, um HTML que carrega arquivos que não vieram. Quando uma regra dispara, a solicitação vai para revisão humana.

**Custo.** As regras só pegam o que foi previsto. Um texto bem formado e errado passa pelas regras e depende da revisão humana.

## 6. Quem escreve código roda depois dos outros

**Contexto.** No teste da batalha naval, as skills rodavam juntas, e o código foi escrito sem ver os requisitos de acessibilidade e o plano de testes que outras skills já tinham entregado.

**Decisão.** Quando a solicitação pede arquivos, as skills que declaram saída de código rodam numa segunda etapa e recebem só as linhas de requisito das outras, em até 2.500 caracteres ([`team_context.py`](../../backend/app/services/team_context.py)). Se uma delas devolver só um plano, tenta de novo uma vez, sem o contexto.

**Custo.** A orquestração fica mais lenta, porque as duas etapas não se sobrepõem. Com o modelo gratuito, mandar os documentos inteiros piorou o código, por isso vai só o resumo.

## 7. Acesso por propriedade, visibilidade e cota, sem papéis

**Contexto.** Os papéis de usuário não correspondiam a quem de fato podia mexer em cada coisa.

**Decisão.** Quem criou a solicitação ou a skill pode mexer nela. A visibilidade da skill (oficial, privada ou de comitê) diz quem pode usá-la, e a cota diária de tokens limita o gasto de cada pessoa. Detalhes em [SECURITY.md](../../SECURITY.md#autorização).

**Custo.** Não há uma pessoa administradora geral. A conta inicial só liga e desliga as skills oficiais sem dono.

## 8. A orquestração roda em segundo plano

**Contexto.** O proxy do Static Web Apps desiste de uma chamada a `/api` depois de 45 s, e uma orquestração com várias skills leva minutos.

**Decisão.** O endpoint devolve na hora, e a execução continua numa tarefa asyncio ([`orchestration_runner.py`](../../backend/app/services/orchestration_runner.py)). A tela acompanha pela linha do tempo da solicitação e pode cancelar.

**Custo.** A tarefa vive só no processo do backend. Se ele reiniciar, as execuções em andamento são marcadas como falhas na subida. Isso supõe um único processo; com vários, seria preciso uma fila.

## 9. OpenRouter como Model Gateway

**Contexto.** O projeto precisa comparar modelos sem reescrever a integração.

**Decisão.** Uma interface de provedor ([`llm/base.py`](../../backend/app/llm/base.py)) com a OpenRouter como implementação principal. Produção usa `openai/gpt-5-mini`; o desenvolvimento e os testes com modelo real usam modelos gratuitos.

**Custo.** Os modelos gratuitos mudam e saem do catálogo sem aviso, e geram código pior. Os resultados medidos com eles estão registrados como tal nas [evidências](../validation/evidence/).

## 10. Repositório do GitHub como base de conhecimento do comitê

**Contexto.** A base de conhecimento era única para todos, com documentos de exemplo. Um comitê real precisa que os agentes conheçam o código do próprio sistema.

**Decisão.** Um membro adiciona um repositório público do GitHub ao comitê, e a indexação roda em segundo plano: baixa o código, lê os arquivos de texto e grava os trechos com embeddings ligados ao comitê ([`repository_service.py`](../../backend/app/services/repository_service.py)). A busca da orquestração passa a ver a base global mais os repositórios do comitê da solicitação, nunca os de outro. É a fase 1. A fase 2 monta um grafo do código (arquivos, imports e definições) e um Agente do Repositório que segue esse grafo para achar as fontes.

**Custo.** Só repositórios públicos: um privado exigiria pedir mais permissão no login com GitHub. Os trechos são janelas de texto, sem entender a estrutura do código, até a fase 2. Indexar gasta embeddings (cerca de 1 centavo de dólar por MB de código com o modelo de produção), por isso há limites. Como a orquestração, a indexação vive no processo do backend, e um reinício no meio marca o repositório como falho.
