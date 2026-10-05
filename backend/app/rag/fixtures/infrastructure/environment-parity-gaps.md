# Lacunas de paridade entre ambientes — Aplicação Financeira Legada

> Registrado depois de um incidente em que uma mudança passou no ambiente
> de teste e falhou em produção por causa de uma diferença de ambiente não
> documentada até então.

## Diferenças conhecidas entre teste e produção

- **Versão de banco**: produção roda uma versão mais antiga do motor de
  banco de dados que o ambiente de teste — uma query que funciona num
  ambiente pode ter comportamento ou performance diferente no outro.
- **Volume de dados**: o ambiente de teste tem uma fração pequena dos
  clientes de produção (~200 contra a base real, ver
  `performance/riskbatchjob-performance-profile.md` para a contagem em
  produção). Problemas de performance como o N+1 do `RiskBatchJob` não
  aparecem no ambiente de teste — só se manifestam com o volume real.
- **Credencial e configuração**: o arquivo `.properties` de configuração
  (ver `deployment-process-notes.md`) é mantido e editado separadamente em
  cada ambiente, manualmente — já houve caso de uma configuração nova ser
  aplicada só em produção e esquecida no ambiente de teste, ou vice-versa.

## Incidente que motivou este levantamento

Uma mudança no `OrderApprovalController` foi validada no ambiente de
teste e aprovada para produção. Em produção, com o volume real de pedidos
simultâneos (muito maior que no teste), um comportamento de concorrência
que não aparecia com poucos dados causou aprovações duplicadas em um
pequeno número de casos. O ambiente de teste nunca teria revelado esse
problema, dado o volume de dados muito menor.

## Recomendação registrada (não implementada)

Nenhuma mudança que dependa de volume ou concorrência real deveria ser
considerada "validada" só porque passou no ambiente de teste atual —
registrar essa limitação explicitamente no processo de release até que a
paridade de ambiente (volume de dados e versão de banco) seja corrigida.
