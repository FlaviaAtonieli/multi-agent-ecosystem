# Classificação de dados — tabela CUSTOMER (revisão de segurança/privacidade)

> Levantamento de classificação de dados pessoais para fins de LGPD, feito
> sobre o schema legado do módulo financeiro.

## Classificação por coluna (`CUSTOMER`)

| Coluna       | Classificação        | Observação |
|--------------|-----------------------|------------|
| `ID`         | Identificador interno | Não é dado pessoal isoladamente. |
| `NOME`       | Dado pessoal          | Identifica diretamente a pessoa/empresa cliente. |
| `EMAIL`      | Dado pessoal (PII)    | Sujeito à LGPD; hoje sem máscara em nenhuma saída do sistema. |
| `SEGMENTO`   | Uso interno           | Classificação comercial, não é dado pessoal sensível. |
| `CRIADO_EM`  | Metadado              | Sem risco de privacidade isolado. |

## Exposição conhecida

- `FinanceReportService` inclui `EMAIL` no relatório financeiro mensal, sem
  mascaramento, mesmo quando o relatório é usado só para totais agregados de
  exposição de crédito — o e-mail individual não é necessário para esse caso
  de uso, mas está presente hoje.
- Não há registro de quem acessou o relatório mensal depois de gerado
  (mesma lacuna de auditoria descrita em `access-control-notes.md`).
- Não existe rotina de expurgo/anonimização para clientes inativos há muito
  tempo — os dados de `CUSTOMER` permanecem indefinidamente.

## Enquadramento LGPD (observação, não parecer jurídico)

O tratamento do campo `EMAIL` hoje não tem finalidade restrita documentada
nem prazo de retenção definido, o que é uma lacuna frente aos princípios de
finalidade e necessidade da LGPD (Art. 6º). Qualquer mudança no módulo
financeiro que amplie o uso do e-mail do cliente (ex.: notificações
automáticas de limite) deveria vir acompanhada de uma revisão desse ponto,
não presumir que o uso atual já está coberto.
