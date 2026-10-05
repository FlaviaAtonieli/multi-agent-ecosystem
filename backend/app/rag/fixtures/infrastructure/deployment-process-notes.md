# Notas do processo de deploy — Aplicação Financeira Legada

> Runbook informal, mantido por quem fazia os deploys até sair do time em
> 2022. Ninguém revisou ou atualizou desde então. Complementa
> `architecture/deployment-topology.md` (onde cada componente roda) com
> como eles chegam lá.

## Processo de deploy hoje

1. Dev gera o build localmente (`.jar` do monólito, inclui
   `OrderApprovalController`, `RiskBatchJob`, `FinanceReportService` e
   `CustomerRepository` — ver `architecture/deployment-topology.md`).
2. Dev copia o `.jar` pro servidor via `scp` manual.
3. Dev conecta via SSH, para o processo antigo, substitui o `.jar`, sobe o
   processo novo.
4. Verificação pós-deploy: dev olha o log por alguns minutos e confirma
   "parece ok" manualmente — sem suíte de smoke test automatizada.

## Não existe

- Pipeline de CI/CD: nenhuma etapa automatizada entre o commit e o deploy —
  tudo é feito manualmente pelo passo a passo acima.
- Infraestrutura como código: o servidor foi provisionado manualmente uma
  vez, há anos; não há script ou manifesto que recrie o ambiente do zero.
- Rollback automatizado: reverter significa repetir o processo manual com
  o `.jar` da versão anterior, se alguém ainda tiver guardado uma cópia.
- Ambiente de staging com paridade: existe um ambiente "de teste", mas
  roda numa versão de banco diferente da produção e não recebe o mesmo
  volume/formato de dados (ver `environment-parity-gaps.md`).

## Risco identificado

A mesma credencial de banco compartilhada entre `OrderApprovalController`,
`RiskBatchJob` e `FinanceReportService` (já apontada em
`security/access-control-notes.md` como risco de controle de acesso) é
hoje gerenciada como uma linha num arquivo `.properties` copiado
manualmente pro servidor a cada deploy — sem cofre de segredos, sem
rotação, sem histórico de quem alterou.

## Recomendação registrada (não implementada)

Automatizar build e deploy (mesmo que um pipeline simples), adotar um
cofre de segredos para a credencial de banco em vez do arquivo
`.properties` copiado manualmente, e alinhar o ambiente de staging à
versão de banco de produção antes de confiar nele como gate de qualidade.
