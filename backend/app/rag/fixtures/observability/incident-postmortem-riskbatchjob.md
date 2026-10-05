# Postmortem — RiskBatchJob parou de rodar por 6 dias sem alerta (2023)

> Registrado pelo time de Operações após o incidente ser descoberto
> manualmente pelo Financeiro, não por monitoramento. Sem Trace ID — sistema
> anterior a este ecossistema, incidente real no módulo `legacy_billing`.

## Linha do tempo

1. **Dia 0**: uma migração de infraestrutura mudou a credencial de banco
   usada pelo `RiskBatchJob` (ver `security/access-control-notes.md` — os
   três consumidores de `CreditLimitService` compartilham a mesma
   credencial). O job noturno passou a falhar na conexão.
2. **Dias 1 a 5**: o job falhou silenciosamente todas as noites. Nenhum
   alerta disparou — não existe verificação de "o job rodou e terminou
   hoje", só um log local no servidor que ninguém monitora ativamente.
3. **Dia 6**: o Financeiro percebeu que o relatório de exposição de risco
   (gerado por `FinanceReportService`, que depende dos dados que o
   `RiskBatchJob` deveria ter atualizado) estava com números de 6 dias
   atrás. Abriram chamado perguntando se o sistema estava "travado".
4. **Dia 6 (mesma tarde)**: Operações encontrou o erro de conexão nos logs
   locais do servidor do job, corrigiu a credencial, rodou o job manualmente
   para os 6 dias perdidos.

## Causa raiz

Falta de observabilidade, não falha de lógica de negócio: o job falhou de
forma correta e previsível (credencial inválida), mas **nenhum sinal saiu do
sistema** — sem métrica de execução, sem alerta de job ausente, sem dashboard
que mostrasse "última execução bem-sucedida". A detecção dependeu de alguém
de negócio notar um número desatualizado.

## Ação registrada (não implementada)

Instrumentar `RiskBatchJob`, `OrderApprovalController` e
`FinanceReportService` com métricas básicas (execução concluída, duração,
taxa de erro) e um alerta de "job não rodou nas últimas 24h" — nenhum dos
três componentes emite métrica ou log estruturado hoje, só texto livre em
arquivo local.
