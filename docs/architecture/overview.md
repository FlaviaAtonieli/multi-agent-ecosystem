# Visão da Arquitetura

## Objetivo

Validar uma arquitetura de integração de agentes especialistas em ambientes corporativos. O foco não é criar um agente universal, mas coordenar capacidades com responsabilidades, contratos e limites definidos: uma solicitação técnica é qualificada, ganha um `Trace ID`, vai para as Agent Skills de um comitê, passa pelo Quality Gate e pode ser reconstruída pela auditoria.

Os diagramas C4 e os requisitos estão na [RFC](../rfc/). Este documento descreve o que está implementado.

## Decisão estrutural

**Monólito modular** com dois projetos e PostgreSQL. Reduz o custo operacional da Prova de Conceito sem misturar responsabilidades. Separar em serviços só se justifica com requisitos concretos de escala ou isolamento. A exceção são as Agent Skills, que rodam como processos MCP.

```text
frontend/  React, Vite e TypeScript: interface. Nunca decide autorização.
backend/   FastAPI e SQLAlchemy: regras, autorização, persistência e auditoria.
```

## Módulos do backend

| Pasta em `backend/app/` | Responsabilidade |
|---|---|
| `api/` | Rotas REST e documentação OpenAPI |
| `services/` | Orquestração, comitês, arquivos, sugestão de skills, autenticação e LLM |
| `agent_catalog/` | Catálogo de skills, cliente MCP, servidores MCP e contratos |
| `agent_manifest/` | Leitura e validação do manifesto `modelo.md` |
| `quality_gate/` | Regras explícitas sobre as respostas das skills |
| `llm/` | Provedores de modelo, prompts e mascaramento de dados |
| `rag/` | Indexação, embeddings, busca e métricas |
| `models/`, `schemas/` | Tabelas e contratos da API |
| `core/` | Configuração, segurança, limites de requisição e métricas |
| `db/` | Conta inicial e cadastros iniciais (seeds) |

## Fluxo de uma orquestração

```text
Pessoa autenticada
  -> cria a solicitação e escolhe o comitê (pode pedir sugestões de skills fora dele)
  -> contexto avaliado: AWAITING_CONTEXT ou QUALIFIED, com Trace ID
  -> POST /start responde na hora, e a execução segue em segundo plano
  -> para cada skill ativa do comitê, até 3 ao mesmo tempo, por MCP:
       mascaramento -> busca na base (RAG) -> modelo -> contrato de saída
  -> arquivos gerados são validados e guardados
  -> Quality Gate aprova ou pede revisão humana
  -> resposta consolidada
  -> a tela acompanha cada etapa pela linha do tempo
```

Detalhes da IA no [Pipeline de IA](ai-pipeline.md).

## Agent Skills

- **Execução por MCP real**, com o SDK oficial. O Orquestrador é o cliente (`agent_catalog/mcp_client.py`). Em produção, cada chamada usa um subprocesso por stdio, que nunca fica exposto à rede.
- **Um executor e um servidor para todas as skills** (`agent_catalog/tool_interface.py` e `mcp_servers/skill_server.py`). O que muda de uma skill para outra está nos dados: a área, a persona do manifesto e as frases sobre a evidência. Até 08/11/2026 eram 5 executores e 5 servidores quase iguais (86% a 95% de texto em comum).
- **Extensibilidade:** uma skill nova, em qualquer área, entra por formulário ou manifesto, sem mudança no núcleo do Orquestrador.

## Limites arquiteturais

- O frontend nunca recebe chaves de provedor, e a autorização é sempre validada no backend.
- O token de sessão fica só no cookie do navegador, e o banco guarda o hash.
- Uma chamada de modelo não habilita executor nem altera permissões.
- A Prova de Conceito só recomenda: nada gerado pelo modelo é executado, e a decisão final é humana.
- A execução em segundo plano assume **um único processo** no backend.
- A busca roda em memória, sem índice vetorial, o que serve ao volume atual, mas não a uma base grande.
- A base de conhecimento não é separada por área: o nome da área só influencia o texto da consulta.
