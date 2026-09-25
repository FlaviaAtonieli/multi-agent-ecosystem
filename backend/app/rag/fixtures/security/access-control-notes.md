# Notas de controle de acesso — Módulo Financeiro Legado (revisão de segurança)

> Anotações de uma revisão informal de segurança feita em 2022. Não houve
> pentest formal nem correção registrada para os pontos abaixo.

## Pontos positivos identificados

- `CustomerRepository` usa `PreparedStatement` em todas as consultas
  (`findById`, `getTotalUtilizado`) — sem concatenação de string no SQL, sem
  superfície de SQL injection nesses dois métodos.

## Riscos identificados

1. **Credencial de banco compartilhada**: `OrderApprovalController`,
   `RiskBatchJob` e `FinanceReportService` usam a mesma credencial de conexão
   com o banco — nenhum dos três tem permissão restrita (ex.: o job noturno,
   que só deveria ler dados de risco, tem a mesma permissão de escrita que o
   caminho de aprovação de pedido). Viola o princípio de menor privilégio.
2. **Sem log de auditoria em leituras de limite de crédito**: chamadas a
   `CreditLimitService.getLimiteCredito()` não geram nenhum registro de quem
   consultou o limite de qual cliente e quando — só existe rastreabilidade
   para a decisão final de aprovação/rejeição do pedido, não para a consulta
   em si.
3. **Sem controle de acesso por perfil dentro do módulo**: qualquer código
   com acesso à `CustomerRepository` pode ler o limite de crédito e o total
   utilizado de qualquer cliente — não há verificação de que o chamador tem
   relação com aquele cliente específico.

## Recomendação registrada (não implementada)

Introduzir logging estruturado nas três operações de leitura (limite,
total utilizado, dados do cliente) com o identificador do processo
chamador, e revisar a credencial de banco do `RiskBatchJob` para um usuário
com permissão só de leitura sobre `CUSTOMER` e `CUSTOMER_ORDER`.
