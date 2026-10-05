# Auditoria de conformidade LGPD — Módulo de Limite de Crédito (2023)

> Levantamento inicial feito pelo Jurídico junto com um dev emprestado do
> time, antes de qualquer adequação formal à LGPD. Não houve relatório de
> impacto (RIPD) nem registro formal das atividades de tratamento (ROPA)
> até a data deste documento.

## Dados pessoais identificados

`CUSTOMER` (ver `legacy_billing/schema.sql`) guarda `NOME` e `EMAIL` em
texto plano, sem nenhuma camada de criptografia em repouso específica para
esses campos (só o que o banco já provê por padrão, se provê). `SEGMENTO`
não é dado pessoal isoladamente, mas combinado com `NOME`/`EMAIL` compõe um
perfil do cliente.

## Lacunas identificadas

1. **Sem base legal documentada**: nenhum campo ou tabela registra sob qual
   base legal (consentimento, execução de contrato, etc.) os dados de cada
   cliente são tratados. `register_skill`/`CustomerRepository` não têm
   conceito de finalidade de tratamento.
2. **Sem política de retenção**: não existe rotina que apague ou anonimize
   dados de clientes inativos — uma linha em `CUSTOMER` criada em 2015
   permanece indefinidamente, mesmo sem nenhum pedido associado há anos.
3. **Sem fluxo de direito do titular**: não há endpoint nem processo manual
   documentado para atender pedido de acesso, correção ou eliminação de
   dados pessoais (Art. 18 da LGPD). Pedido hoje exigiria uma query manual
   direto no banco por alguém com acesso, sem trilha de auditoria
   específica para esse tipo de acesso.
4. **Exportação sem anonimização**: `FinanceReportService` gera relatório
   mensal de exposição de crédito citando clientes por `NOME` — não existe
   variante anonimizada/pseudonimizada do relatório, mesmo quando a
   finalidade (acompanhar exposição agregada por segmento) não exigiria
   identificar cada cliente individualmente.

## Recomendação registrada (não implementada)

Antes de qualquer expansão do módulo (ex.: a segmentação da CR-2019-114, que
aumentaria o uso do campo `SEGMENTO` combinado a dados pessoais), definir
política de retenção, registrar base legal por finalidade de tratamento, e
avaliar pseudonimização no relatório mensal — hoje o módulo trata dado
pessoal sem nenhuma dessas salvaguardas.
