# Regras de Negócio — Módulo Financeiro (documentação parcial, desatualizada)

> Documento migrado do wiki antigo em 2020. Vários trechos ficaram incompletos
> depois da reorganização das pastas. Manter aqui até alguém revisar.

## Limite de crédito

- Hoje todo cliente tem o mesmo limite de crédito: **R$ 5.000,00**, fixo em
  `CreditLimitService.LIMITE_GLOBAL`.
- O campo `SEGMENTO` do cliente (varejo, atacado, corporativo) existe no banco
  desde 2019, mas **não é usado** no cálculo do limite atualmente.
- Pontos do sistema que dependem do limite de crédito atual:
  1. Aprovação de pedido (`OrderApprovalController`) — bloqueia pedido acima
     do limite disponível.
  2. Job noturno de recálculo de risco (`RiskBatchJob`) — roda toda madrugada
     e reavalia clientes inadimplentes.
  3. Relatório financeiro mensal (`FinanceReportService`) — usa o limite para
     calcular exposição de crédito da carteira.

## Segmentação de clientes (parcialmente implementada)

- Segmentos cadastrados hoje: `VAREJO`, `ATACADO`, `CORPORATIVO`.
- [PENDENTE] Não há regra de negócio formal definindo limites diferentes por
  segmento — isso nunca foi implementado, apesar do campo existir.
- Um pedido antigo de mudança (2019) sugeria: `ATACADO` e `CORPORATIVO`
  deveriam ter limite maior que `VAREJO`, mas o valor exato nunca foi definido
  e o ticket original foi arquivado sem solução.

## Risco conhecido

Se o limite de crédito passar a variar por segmento, qualquer código que hoje
assume "todo cliente tem o mesmo limite" (relatórios, cache, testes antigos)
pode ficar inconsistente até ser atualizado. Não existe teste automatizado
cobrindo esse cenário hoje.
