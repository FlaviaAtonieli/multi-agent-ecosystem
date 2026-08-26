# Visão da Arquitetura

## Objetivo

A aplicação serve como base para validar uma arquitetura de integração de agentes especialistas em ambientes corporativos. O foco não é criar um agente universal, mas coordenar capacidades com responsabilidades, contratos e limites definidos.

A PoC deve permitir que uma solicitação técnica seja qualificada, associada a um `Trace ID`, encaminhada às capacidades adequadas, validada e reconstruída posteriormente por meio dos registros de auditoria.

## Decisão estrutural

A primeira versão adota um **monólito modular** com dois projetos:

- `frontend`: interface, navegação e estado de apresentação;
- `backend`: autenticação, autorização, regras, persistência, integração com modelos e auditoria.

O PostgreSQL mantém os dados de usuários, sessões, solicitações, execuções e invocações. O Docker Compose organiza o ambiente local.

Essa estrutura foi escolhida para reduzir o custo operacional da PoC sem misturar responsabilidades de domínio. A separação em serviços independentes pode ser avaliada quando existirem requisitos concretos de escala ou isolamento.

## Componentes implementados

### Frontend

- cliente HTTP;
- contexto de autenticação;
- rotas públicas e protegidas;
- login e cadastro;
- dashboard;
- criação de solicitação;
- consulta de histórico e timeline.

O frontend adapta a experiência conforme o usuário autenticado, mas não decide autorização. Todas as verificações de acesso permanecem no backend.

### Backend

- API REST;
- autenticação por sessão opaca;
- proteção CSRF;
- controle de perfis;
- persistência e migrations;
- auditoria de eventos;
- solicitações técnicas;
- qualificação inicial do contexto;
- execuções de orquestração;
- abstração de provedores de modelo, incluindo OpenRouter como gateway primário (múltiplos providers/modelos por trás de uma única credencial) e o adaptador direto OpenAI como integração opcional;
- pipeline de recuperação aumentada de geração (RAG): indexação de artefatos em `knowledge_chunks`, recuperação por similaridade antes de cada chamada de modelo, e registro do evento `RAG_RETRIEVAL_COMPLETED` na timeline;
- rastreabilidade individual das invocações, incluindo os trechos recuperados que fundamentaram cada resposta;
- catálogo de Agent Skills: criação assistida (RF01), importação e validação estrutural de manifesto `modelo.md` (RF02/RF03), registro no catálogo (RF04) e habilitação/desabilitação por administrador (RF16);
- seleção de Agent Skills por domínio da solicitação e execução coordenada (RF08/RF09/RF10), com uma primeira skill de referência ("Código Legado") operando sobre o pipeline RAG completo;
- Quality Gate baseado em regras explicáveis (schema válido, nível de confiança, divergência entre respostas do mesmo domínio) consolidando as respostas antes da entrega (RF11).

## Componentes previstos no RFC

Os módulos abaixo fazem parte do desenho da PoC, mas ainda não estão completos na implementação atual:

- Agent Builder com editor visual (a criação assistida hoje é via API/formulário estruturado, sem UI dedicada);
- mais de uma Agent Skill executável (só "Código Legado" tem executor real; "Regras de Negócio" e "Arquitetura" podem ser registradas no catálogo, mas ainda não têm execução implementada);
- perfil específico de revisão (`REVIEWER`).

Já implementados (ver seção anterior): importador de `modelo.md`, validador de manifesto, catálogo de Agent Skills, camada de contratos de entrada e saída (Apêndice C), seleção dinâmica de Agent Skills por domínio, execução coordenada de especialistas e Quality Gate.

A documentação distingue esses dois estados para não apresentar como concluído o que ainda está em desenvolvimento.

## Fluxo atual

```text
Interface web
  -> API de solicitações
  -> validação de contexto
  -> criação do Trace ID
  -> persistência da solicitação e da execução
  -> registro dos eventos
  -> consulta no dashboard e na timeline
```

Quando a integração com modelos está habilitada:

```text
Solicitação QUALIFIED
  -> verificação de perfil e propriedade
  -> sanitização e limite de entrada
  -> recuperação de trechos relevantes na base de conhecimento (RAG)
  -> criação do LLM Call ID
  -> provedor configurado (OpenRouter, OpenAI ou mock)
  -> validação da resposta estruturada
  -> persistência de metadados, hashes e trechos recuperados
  -> aprovação humana obrigatória
```

## Limites arquiteturais

- O frontend nunca recebe chaves de provedor.
- A autorização é validada no backend.
- O token bruto da sessão permanece apenas no cookie do navegador.
- O banco armazena o hash do token de sessão.
- Credenciais, cookies e senhas não devem aparecer nos logs.
- Uma chamada de modelo não pode habilitar um executor nem alterar permissões.
- A PoC atua em modo consultivo e read-only.
- A decisão final permanece sob responsabilidade humana.
- O retrieval do pipeline RAG roda em memória (sem `pgvector`/índice ANN), adequado ao volume da fixture da PoC; é um limite conhecido, não uma limitação arquitetural permanente.

## Evolução prevista

A expansão seguirá módulos de domínio, sem concentrar toda a lógica no serviço de orquestração:

```text
rag/               (implementado)
agent_manifest/    (implementado)
agent_catalog/     (implementado)
quality_gate/      (implementado)
interaction_advisor/
orchestration/
traceability/
```

`rag/` já existe (`app/rag/`): interfaces `Retriever`/`EmbeddingProvider`, retrieval em memória por similaridade de cosseno (sem `pgvector` nesta fase — ver "Limites arquiteturais"), e uma fixture sintética de código legado usada como base de conhecimento inicial.

`agent_manifest/` (`app/agent_manifest/`) faz o parsing e a validação estrutural do manifesto `modelo.md` (Apêndice G do RFC). `agent_catalog/` (`app/agent_catalog/`) mantém o registro de Agent Skills e as expõe via **MCP real**, usando o SDK oficial `mcp` (não mais um contrato só inspirado no protocolo): cada domínio com executor tem um servidor MCP próprio em `agent_catalog/mcp_servers/` (`MCPServer` + `@mcp.tool()`, com `input_schema`/`output_schema` derivados automaticamente dos mesmos modelos Pydantic do Apêndice C), e o Orquestrador o consome como cliente MCP via `agent_catalog/mcp_client.py`. Dois transportes são suportados pelo mesmo SDK: `stdio` (subprocesso real, JSON-RPC de verdade — padrão em produção) e "em memória" (mesmo processo, usado pelos testes para manter a suíte rápida). O subprocesso é gerado diretamente pelo Orquestrador (nunca exposto à rede) e herda a confiança do processo pai — por isso não implementamos o framework de Authorization do MCP (OAuth 2.1 resource server), pensado para acesso remoto/não confiável. `quality_gate/` (`app/quality_gate/`) aplica regras explicáveis (schema válido, nível de confiança, divergência textual) sobre as respostas consolidadas, sem depender de um segundo modelo como juiz.

`interaction_advisor/`, `orchestration/` e `traceability/` continuam sem módulo dedicado: suas responsabilidades já existem, hoje concentradas em `orchestration_service.py`/`OrchestrationEvent` — extrair módulos próprios é reorganização, não capacidade nova, e fica como evolução futura.

Cada módulo deve definir:

- contrato de entrada;
- contrato de saída;
- serviço de aplicação;
- persistência necessária;
- endpoints;
- eventos de auditoria;
- testes.

A principal prova de extensibilidade será a inclusão de uma nova Agent Skill por manifesto e contrato, sem alteração no núcleo do Orquestrador.
