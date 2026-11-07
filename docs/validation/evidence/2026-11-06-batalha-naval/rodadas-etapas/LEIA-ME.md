# Rodadas da orquestração em duas etapas (trabalho em andamento)

Saídas brutas das rodadas locais com o modelo gratuito `dots-studio/dots-3-note-preview:free`, guardadas para a análise continuar. **Ainda não é evidência final.**

- `v1-contexto-completo/`: o programador recebeu os documentos inteiros (~6 mil caracteres). As 3 rodadas pioraram: jogo quebrado, plano em vez de código e nenhum arquivo.
- `v2-contexto-enxuto/`: só as linhas de requisito (~2.300 caracteres), com nova tentativa sem contexto quando não vem código.
  - Rodada 1: veio código, mas com erros de JavaScript.
  - Rodada 2: veio código, mas o computador espera 1 s para jogar, e o teste precisou passar a esperar.
  - Rodada 3: sem código mesmo depois da nova tentativa.

Linha de base, o jogo de uma etapa só: 13 de 17 no `playtest-caixa-preta.js`.

A pontuação das rodadas da v2 com o teste corrigido (que espera a jogada do computador) ficou pela metade quando o trabalho foi interrompido.

Até aqui, os dados indicam que o limite é o modelo gratuito, e não a orquestração. O próximo passo proposto é repetir com o modelo pago de produção, com autorização.
