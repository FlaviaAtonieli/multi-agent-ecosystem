# Perfil de performance — RiskBatchJob (profiling pontual, 2023)

> Feito pelo mesmo time de Operações que escreveu o postmortem de
> observabilidade (`observability/incident-postmortem-riskbatchjob.md`),
> depois de perceber que o job estava demorando mais a cada mês. Profiling
> manual com cronômetro e log local — não há métrica de duração automática
> (ver `observability/logging-metrics-gaps.md`).

## Padrão de execução observado

`RiskBatchJob` itera **sequencialmente** sobre todos os clientes
(`CUSTOMER`) e, para cada um, chama
`CustomerRepository.getTotalUtilizado(customerId)` — uma consulta SQL
separada por cliente (clássico N+1: N clientes, N round-trips ao banco, em
vez de uma única consulta agregada por `CUSTOMER_ID`).

## Causa estrutural identificada

`CUSTOMER_ORDER` tem uma foreign key para `CUSTOMER_ID`
(`schema.sql`), mas **nenhum índice declarado nessa coluna** além da FK
implícita. Cada chamada de `getTotalUtilizado` faz, na prática, uma
varredura maior do que precisaria sobre `CUSTOMER_ORDER` — e isso se repete
uma vez por cliente, toda noite, sequencialmente, sem paralelismo nem
batching.

## Números registrados no profiling

- ~8.000 clientes ativos no momento do levantamento.
- ~45ms médios por chamada de `getTotalUtilizado` (medição manual, variável).
- Tempo total estimado do job: ~6 minutos só nessa etapa — crescendo de
  forma aproximadamente linear com o número de clientes, já que não há
  batching.
- Janela de execução noturna disponível: 2 horas (compartilhada com outros
  jobs batch do mesmo servidor, não listados aqui).

## Risco identificado

Como o crescimento é linear por cliente e a base de clientes está
crescendo, o job pode eventualmente se aproximar do limite da janela
noturna disponível — sem alerta de duração (ver lacuna de observabilidade),
ninguém saberia até o job começar a atrasar os jobs seguintes na fila.

## Recomendação registrada (não implementada)

Substituir o loop N+1 por uma única consulta agregada
(`SELECT CUSTOMER_ID, SUM(VALOR_TOTAL) ... GROUP BY CUSTOMER_ID`) e avaliar
um índice em `CUSTOMER_ORDER(CUSTOMER_ID, STATUS)` — a mesma combinação já
usada no `WHERE` de `getTotalUtilizado`.
