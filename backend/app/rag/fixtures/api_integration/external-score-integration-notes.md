# Integração com serviço externo de score — Módulo de Limite de Crédito

> Levantamento técnico sobre a única integração externa do módulo,
> adicionada em 2020 por um dev que já saiu do time. Sem documentação de
> contrato formal (OpenAPI ou similar) encontrada.

## O que a integração faz

`OrderApprovalController` chama um serviço externo de score de crédito
(`BureauScoreClient.consultarScore(customerId)`) como um sinal adicional
antes de aprovar um pedido — síncrono, no mesmo caminho crítico já descrito
em `architecture/module-dependency-map.md` e
`performance/capacity-planning-notes.md`.

## Como a chamada é feita

- REST síncrono via HTTP, direto do `OrderApprovalController` — sem
  camada de abstração ou cliente gerado a partir de um contrato formal.
- Sem timeout configurado explicitamente (usa o padrão da biblioteca HTTP,
  nunca verificado).
- Sem circuit breaker: se o serviço externo ficar lento ou indisponível, a
  aprovação de pedido trava esperando a resposta (ou o timeout padrão,
  desconhecido).
- Sem teste de contrato (contract test) entre o módulo e o serviço
  externo — a única forma de saber se a integração ainda funciona é rodar
  manualmente em produção.

## Versionamento

Nenhum. A URL chamada não inclui versão (`/score/{customerId}`, sem
`/v1/` ou equivalente) — uma mudança no formato de resposta do lado
externo quebra o cliente sem aviso prévio, já que não há contrato
versionado nem notificação de mudança (ver `breaking-change-incident.md`
para um caso real disso acontecendo).

## Recomendação registrada (não implementada)

Introduzir timeout explícito e circuit breaker na chamada, negociar
versionamento de URL com o provedor externo, e criar um teste de contrato
que rode no pipeline (quando um pipeline existir — ver
`infrastructure/deployment-process-notes.md`) para detectar quebra de
contrato antes de produção.
