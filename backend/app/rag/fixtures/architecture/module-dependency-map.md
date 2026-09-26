# Mapa de dependências — Módulo de Limite de Crédito (nota arquitetural)

> Levantamento técnico informal, feito por um arquiteto que passou pelo time em
> 2022. Não há ADR formal registrado para nenhuma das decisões abaixo.

## Consumidores diretos de `CreditLimitService.getLimiteCredito()`

1. `OrderApprovalController` (camada web) — chama direto, síncrono, no
   caminho crítico da aprovação de pedido.
2. `RiskBatchJob` (job noturno) — chama em lote, para todos os clientes,
   toda madrugada.
3. `FinanceReportService` (geração de relatório mensal) — chama sob demanda,
   ao montar o relatório de exposição de crédito.

Nenhum desses três consumidores usa uma interface comum além do método direto
da classe concreta `CreditLimitService` — não existe uma abstração
(`CreditLimitPolicy` ou equivalente) entre eles e a implementação. Acoplamento
direto à classe concreta.

## Risco estrutural identificado

Como não há camada de abstração, **qualquer mudança na regra de cálculo do
limite precisa ser testada nos três pontos de consumo**, não só na classe em
si. Hoje não existe teste automatizado cobrindo os três juntos — cada
consumidor tem (ou não tem) sua própria cobertura isolada.

Recomendação registrada (nunca implementada): extrair uma interface
`CreditLimitPolicy` com uma implementação `FixedGlobalLimitPolicy` (o
comportamento atual) e, quando a segmentação for decidida (ver
`business_rules/change-request-history.md`, CR-2019-114), uma
`SegmentedLimitPolicy` nova — sem alterar os três consumidores, só trocando a
implementação injetada.

## Acoplamento com a camada de dados

`CreditLimitService` depende de `CustomerRepository`, que acessa `CUSTOMER` e
`CUSTOMER_ORDER` via JDBC puro, sem camada de ORM ou repositório abstrato
adicional. Isso significa que o serviço de domínio está diretamente acoplado
aos nomes de coluna do schema legado (`SEGMENTO`, `VALOR_TOTAL`) — uma
mudança de schema exige mudança simultânea no repositório e, por consequência
em cascata, no serviço.
