# Topologia de execução — Módulo Financeiro Legado (nota arquitetural)

> Levantamento técnico informal sobre como os componentes do módulo
> financeiro legado rodam em produção hoje.

## Onde cada componente roda

- `OrderApprovalController`: dentro da aplicação web principal (monólito
  legado em produção), atende requisições síncronas de aprovação de pedido.
- `RiskBatchJob`: **mesmo processo** da aplicação web, disparado por um
  agendador interno (não é um serviço separado nem um cron externo) — roda
  todo dia às 3h da manhã.
- `FinanceReportService`: também no mesmo processo, acionado sob demanda por
  um endpoint interno usado pelo time financeiro.

## Risco estrutural: contenção de recursos

Como `RiskBatchJob` roda no mesmo processo e usa o mesmo pool de conexões de
banco que `OrderApprovalController`, um lote grande de clientes no job
noturno pode competir por conexões com pedidos reais sendo aprovados — hoje
isso é mitigado só porque a madrugada tem baixo volume de pedidos, não por
isolamento de recursos de verdade.

Não existe fila de mensagens, worker separado, ou qualquer desacoplamento
entre o caminho síncrono (aprovação de pedido) e o caminho em lote
(recálculo de risco). Se o volume de clientes crescer, o job noturno pode
passar a impactar a latência de aprovação de pedidos durante a madrugada.

## Observação sobre escalabilidade

Nenhum dos três componentes tem métricas de tempo de execução monitoradas
hoje (ver domínio de Segurança/Observabilidade para a lacuna de logging). Não
há dado histórico sobre quanto tempo o `RiskBatchJob` leva para rodar sobre a
base atual de clientes, o que dificulta prever o ponto em que a contenção de
recursos descrita acima se tornaria um problema visível.
