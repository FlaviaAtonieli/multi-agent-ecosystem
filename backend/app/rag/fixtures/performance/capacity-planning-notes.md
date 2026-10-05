# Notas de capacidade — Módulo de Limite de Crédito

> Rascunho de planejamento de capacidade, nunca formalizado em documento
> oficial. Complementa o perfil de performance do `RiskBatchJob`
> (`riskbatchjob-performance-profile.md`) com o lado do caminho síncrono
> (`OrderApprovalController`).

## Caminho síncrono (`OrderApprovalController`)

Diferente do `RiskBatchJob` (lote, noturno), `OrderApprovalController`
chama `CreditLimitService.getLimiteCredito()` **de forma síncrona, no
caminho crítico da aprovação de pedido** (ver
`architecture/module-dependency-map.md`) — qualquer latência aqui é sentida
diretamente pelo cliente final esperando a aprovação do pedido.

## Ausência de cache

`getLimiteCredito()` hoje retorna um valor constante
(`LIMITE_GLOBAL = R$ 5.000,00`, ver `legacy_billing/business-rules.md`) —
não depende de nenhum dado do cliente ainda. Mesmo assim, não há cache: a
constante é "recalculada" (na prática, só lida) a cada chamada. Isso não é
um problema de performance hoje (é O(1)), mas **vira um problema real no
dia em que a CR-2019-114 for implementada** (limite por segmento, exigindo
consulta): sem cache desde já no desenho, a primeira implementação da
segmentação tende a repetir o mesmo padrão sem cache do `getTotalUtilizado`,
multiplicando consultas no caminho síncrono.

## Pico de carga conhecido

O time de Produto relatou informalmente picos de pedidos em datas
promocionais (não hoje quantificados em nenhum dashboard — ver lacuna de
observabilidade). Não existe teste de carga registrado para
`OrderApprovalController` nesses cenários, nem SLA de latência definido
para a chamada de aprovação.

## Recomendação registrada (não implementada)

1. Antes de implementar a segmentação (CR-2019-114), desenhar
   `getLimiteCredito()` já pensando em cache por `SEGMENTO` (poucos valores
   possíveis), não por cliente — evita repetir o padrão N+1 do
   `RiskBatchJob` no caminho síncrono.
2. Definir um SLA de latência para o caminho de aprovação e medir picos
   reais de carga antes da próxima data promocional, hoje desconhecidos.
