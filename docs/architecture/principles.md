# Princípios de Arquitetura

Este documento registra regras usadas para orientar decisões de implementação. Alterações que contrariem um princípio devem ser justificadas em uma decisão arquitetural.

## Contratos antes da execução

Solicitações, Agent Skills e respostas devem possuir formatos conhecidos e validados. Texto livre pode fazer parte do contexto, mas não substitui contratos de entrada e saída.

## Autorização no backend

A interface pode ocultar ações conforme o perfil, porém a decisão de acesso é sempre tomada pela API. Nenhuma restrição de segurança pode depender apenas do frontend.

## Extensibilidade controlada

Plug-and-play não significa execução arbitrária. Uma Agent Skill deve possuir manifesto válido, domínio, versão, capacidades, limites e um executor autorizado antes de ser habilitada.

## Atuação read-only

A PoC analisa, recomenda e registra. Ela não faz deploy, commit, alteração em banco corporativo, aprovação de Pull Request ou modificação em ambiente produtivo.

## Rastreabilidade por padrão

Toda solicitação recebe um `Trace ID`. Etapas, decisões, falhas e invocações devem permanecer vinculadas a esse identificador.

## Humano no controle

Respostas podem apoiar uma decisão, mas não substituem a aprovação de um profissional autorizado. Resultados com baixa confiança, conflito ou impacto relevante devem ser encaminhados para revisão.

## Provedor substituível

O restante da aplicação não deve depender diretamente de uma API específica de modelo. A integração ocorre por uma interface interna e por configuração de ambiente.

## Minimização de contexto

Cada componente recebe apenas o conteúdo necessário para sua tarefa. Chaves, tokens, credenciais e dados fora do escopo devem ser removidos ou bloqueados antes do processamento.

## Estado real na interface

Nenhuma tela deve exibir métrica, agente, execução ou resultado que não tenha sido retornado pela API ou persistido no banco. Dados demonstrativos devem estar identificados como exemplos.

## Limitações explícitas

Documentos e telas devem separar funcionalidades implementadas, planejadas e fora do escopo. A PoC não deve ser apresentada como uma plataforma corporativa finalizada.
