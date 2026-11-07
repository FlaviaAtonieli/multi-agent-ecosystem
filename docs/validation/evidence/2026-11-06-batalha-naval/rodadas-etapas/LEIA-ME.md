# Rodadas da orquestração em duas etapas com o modelo gratuito

Saídas brutas das rodadas locais com o modelo gratuito `dots-studio/dots-3-note-preview:free`. A análise está em [`../../2026-11-06-batalha-naval.md`](../../2026-11-06-batalha-naval.md).

- `v1-contexto-completo/`: o programador recebeu os documentos inteiros (~6 mil caracteres). As 3 rodadas pioraram: jogo quebrado, plano em vez de código e nenhum arquivo.
- `v2-contexto-enxuto/`: só as linhas de requisito (~2.300 caracteres), com nova tentativa sem contexto quando não vem código.
  - Rodada 1: veio código, mas com erros de JavaScript.
  - Rodada 2: veio código, mas o computador espera 1 s para jogar, e o teste precisou passar a esperar.
  - Rodada 3: sem código mesmo depois da nova tentativa.

Linha de base, o jogo de uma etapa só: 13 de 17 no `playtest-caixa-preta.js`.

Com o teste corrigido, os jogos da v2 não terminam a partida, e em duas rodadas o navegador travou. Com o modelo pago `gpt-5-mini`, a mesma segunda etapa deu 17 de 17. A conclusão: com o modelo gratuito, o limite é o modelo.
