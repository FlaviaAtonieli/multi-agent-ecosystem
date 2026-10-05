# Notas sobre retenção e minimização de dados — Módulo de Limite de Crédito

> Complementa `lgpd-gap-audit.md`, focado especificamente em retenção e
> minimização (princípios da LGPD Art. 6º) em vez do levantamento geral de
> conformidade.

## Minimização de dados

`CustomerRepository.findById()` sempre seleciona `ID, NOME, SEGMENTO,
EMAIL` juntos (ver `legacy_billing/CustomerRepository.java`), mesmo quando
o chamador só precisa do `SEGMENTO` (ex.: para decidir o limite de
crédito). Não há um método mais restrito que devolva só os campos
necessários para cada caso de uso — todo consumidor recebe o conjunto
completo de dados pessoais, mesmo que use só parte dele.

## Retenção por tipo de dado

- `CUSTOMER`: sem política de expiração. Uma conta encerrada continua com
  `NOME`/`EMAIL` na tabela indefinidamente.
- `CUSTOMER_ORDER`: idem — pedidos antigos (inclusive de clientes
  inativos) nunca são arquivados ou anonimizados, mesmo quando o valor de
  negócio de mantê-los identificáveis já passou.
- Comparação registrada: a página de conta deste próprio ecossistema (não
  o sistema legado) já trata exclusão de conta como desativação lógica com
  scrub de nome/e-mail (ver `README.md`, seção da página `/account`) — o
  sistema legado de limite de crédito nunca recebeu tratamento equivalente.

## Risco prático

Sem minimização nem retenção definida, qualquer vazamento ou acesso
indevido ao módulo expõe mais dado pessoal, de mais clientes (inclusive
inativos há anos), do que o estritamente necessário para as operações que
o sistema realmente executa hoje.

## Recomendação registrada (não implementada)

1. Criar uma consulta mínima (`findSegmentoById`) para os consumidores que
   só precisam do segmento, sem trazer `NOME`/`EMAIL` junto.
2. Definir prazo de retenção para clientes inativos e um processo (manual,
   na ausência de automação) de anonimização após esse prazo.
