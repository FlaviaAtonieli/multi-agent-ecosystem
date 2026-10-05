# Levantamento de lacunas de observabilidade — Módulo de Limite de Crédito

> Feito pelo time de Operações logo após o postmortem do `RiskBatchJob`
> (ver `incident-postmortem-riskbatchjob.md`), para mapear o resto do módulo
> antes que outro componente falhe do mesmo jeito silencioso.

## Situação por componente

- `CreditLimitService.getLimiteCredito()`: sem log estruturado, sem métrica
  de latência ou taxa de erro. A única rastreabilidade existente é a que já
  foi apontada em `security/access-control-notes.md` — e mesmo essa cobre só
  a decisão final de aprovação, não a chamada ao serviço em si.
- `OrderApprovalController`: loga em texto livre no arquivo local do
  servidor web, sem nível de log consistente nem correlação entre as linhas
  de uma mesma requisição (sem request ID). Não é enviado a nenhum sistema
  central de logs.
- `RiskBatchJob`: ver postmortem — nenhuma métrica de execução.
- `FinanceReportService`: nenhum log ou métrica. Só é possível saber que
  rodou quando alguém abre o relatório gerado.

## Dashboards e alertas existentes

Nenhum. Não há painel de observabilidade para o módulo de limite de crédito
— toda a visibilidade operacional de hoje é reativa (alguém de negócio
percebe um número estranho) em vez de proativa (um alerta dispara antes do
Financeiro perceber).

## Recomendação registrada (não implementada)

Antes de qualquer mudança de regra de negócio no módulo (CR-2019-114,
CR-2023-201), instrumentar os quatro componentes com log estruturado
(incluindo request ID / trace ID para correlação) e métricas básicas
(contagem, latência, taxa de erro, última execução bem-sucedida para o job),
com pelo menos um alerta de "job não rodou" e um dashboard mínimo — sem isso,
uma mudança na regra de cálculo pode introduzir um bug silencioso do mesmo
jeito que a falha de infraestrutura do postmortem ficou invisível por 6 dias.
