# Política comercial — Desconto por volume (documento de negócio)

> Mantido pelo time Comercial. Trata de política de preço/desconto, não do
> limite de crédito (ver `change-request-history.md` para isso).

## Regra de desconto vigente

- Pedidos com `VALOR_TOTAL` acima de R$ 10.000,00 recebem 5% de desconto
  automático, aplicado no momento da criação do pedido.
- O desconto **não depende do `SEGMENTO`** do cliente, só do valor do pedido —
  diferente da discussão de limite de crédito, que a diretoria queria
  segmentar (CR-2019-114) e nunca segmentou de fato.
- Clientes `CORPORATIVO` com contrato específico podem ter desconto negociado
  à parte, registrado fora deste sistema (planilha do time Comercial) — **não
  há tabela no schema atual para isso**, é um risco de negócio conhecido
  (divergência entre o que o contrato diz e o que o sistema calcula).

## Política de cancelamento

- Pedido com status `PENDENTE` pode ser cancelado pelo próprio cliente até
  24h após a criação.
- Pedido com status `APROVADO` só pode ser cancelado por um analista do
  backoffice, mediante justificativa registrada.
- Não existe regra de estorno automático de desconto em caso de cancelamento
  parcial — é tratado manualmente hoje.

## Observação de escopo

Esta política de preço e desconto é uma regra de negócio independente da
regra de limite de crédito, mesmo operando sobre os mesmos pedidos
(`CUSTOMER_ORDER`). As duas não devem ser confundidas ao avaliar o impacto de
uma mudança: alterar o cálculo de limite de crédito não afeta a política de
desconto, e vice-versa.
