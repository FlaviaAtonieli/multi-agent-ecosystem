# Histórico de solicitações de mudança — Limite de Crédito (documento de negócio)

> Mantido pelo time de Produto Financeiro. Não é documentação técnica — ver
> `CreditLimitService.java` para a implementação atual.

## CR-2019-114 — Segmentar limite por SEGMENTO do cliente

- Solicitante: Diretoria Comercial.
- Justificativa de negócio: clientes `CORPORATIVO` reclamavam que o limite fixo
  de R$ 5.000,00 era baixo demais para o volume de compra típico do segmento;
  clientes `VAREJO` de risco alto, por outro lado, deveriam ter limite menor
  que o padrão atual.
- Decisão: aprovado em comitê, mas sem definição dos valores exatos por
  segmento — ticket arquivado sem os números fechados.
- Status: **nunca implementado**. O campo `SEGMENTO` foi adicionado ao banco
  na mesma época (migração de 2019), mas a regra de cálculo nunca foi
  atualizada para usá-lo.

## CR-2021-058 — Alçada de aprovação manual acima do limite

- Solicitante: Financeiro (backoffice).
- Regra proposta: pedidos até 20% acima do limite disponível poderiam ser
  aprovados manualmente por um supervisor, em vez de bloqueados automaticamente
  pelo `OrderApprovalController`.
- Status: **rejeitado** pelo comitê de risco — considerado abertura de exceção
  sem controle auditável suficiente na época.

## CR-2023-201 — Revisão do valor fixo do limite global

- Solicitante: Diretoria Financeira.
- Contexto de negócio: R$ 5.000,00 é o mesmo valor desde a migração do sistema
  COBOL original; não houve correção monetária desde então.
- Status: **em avaliação** — depende da CR-2019-114 ser resolvida primeiro,
  já que reajustar um valor único que ainda não é segmentado foi considerado
  "resolver o problema errado" pelo comitê.

## Regra de negócio vigente hoje (resumo)

Enquanto as CRs acima não avançam, a regra de negócio efetivamente em vigor é a
mais simples possível: **todo cliente, independente de segmento, tem direito
ao mesmo limite de crédito de R$ 5.000,00**. Qualquer proposta de mudança nessa
regra depende de decisão de negócio ainda não tomada (valores por segmento),
não é uma limitação técnica do sistema.
