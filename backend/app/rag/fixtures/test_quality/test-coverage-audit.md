# Auditoria de cobertura de testes — Módulo de Limite de Crédito

> Levantamento feito pelo time de QA em 2023, a pedido do Financeiro, antes de
> avaliar a CR-2023-201 (revisão do valor fixo do limite). Não houve
> acompanhamento formal das recomendações abaixo.

## Cobertura atual por componente

- `CreditLimitService.getLimiteCredito()`: 1 teste unitário
  (`testLimiteFixoCincoMil`), cobre só o caminho padrão (cliente sem
  `SEGMENTO` definido). Nenhum teste cobre cliente `CORPORATIVO` ou `VAREJO`
  isoladamente, mesmo com o campo já existindo no banco desde 2019.
- `OrderApprovalController`: sem teste automatizado próprio. A única cobertura
  indireta vem de um teste de integração (`OrderFlowIntegrationTest`) que
  passa pelo caminho de aprovação uma vez, com um único valor de pedido.
- `RiskBatchJob`: sem teste automatizado. O job roda em produção todo dia há
  anos sem nenhuma suíte que valide o comportamento em lote.
- `FinanceReportService`: sem teste automatizado.

## Risco identificado (confirma achado arquitetural já registrado)

Como `module-dependency-map.md` já aponta, os três consumidores de
`getLimiteCredito()` não compartilham uma interface comum. Esta auditoria
confirma a consequência prática: **nenhuma suíte de teste cobre os três
consumidores juntos** — uma mudança na regra de cálculo (ex.: implementar a
segmentação da CR-2019-114) pode quebrar `RiskBatchJob` ou
`FinanceReportService` silenciosamente, sem nenhum teste vermelho avisando,
mesmo que `CreditLimitServiceTest` continue verde.

## Teste instável (flaky) identificado em CI

`OrderFlowIntegrationTest` falha de forma intermitente (~1 a cada 15 execuções
no pipeline) sem relação aparente com o código alterado no PR. Suspeita
registrada no histórico do CI: dependência de ordem de execução com outro
teste que popula a mesma tabela `CUSTOMER_ORDER` sem isolamento de dados
(nenhum dos dois testes limpa o estado que criou). Nunca foi investigado a
fundo — o time reexecuta o pipeline quando falha.

## Recomendação registrada (não implementada)

Criar um teste de regressão que fixe o comportamento atual (limite único de
R$ 5.000,00 para todo `SEGMENTO`) nos três pontos de consumo antes de
qualquer mudança motivada pela CR-2019-114 ou pela CR-2023-201 — hoje não
existe uma rede de segurança que indique se a segmentação foi implementada
corretamente ou se quebrou algum dos três consumidores.
