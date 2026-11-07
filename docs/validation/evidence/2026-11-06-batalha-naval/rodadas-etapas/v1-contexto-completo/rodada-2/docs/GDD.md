# Game Design Document - Batalha Naval

## Introdução
- **Trace ID:** TRC-20261107-36F910
- **Título:** Jogo de Batalha Naval
- **Tipo:** Jogo de tabuleiro para navegador (HTML, CSS, JavaScript puro)
- **Jogadores:** 1 Humano vs. Computador

## Preparação
- **Tabuleiro:** 10x10 para cada jogador.
- **Frota Computador:** Porta-aviões (5), Encouraçado (4), Cruzador (3), Submarino (3), Destróier (2). Posicionamento aleatório, sem sobreposição, antes do início.
- **Frota Humano:** Mesma composição. Posicionamento aleatório (automático) para simplificar esta versão.
- **Interface:** Dois tabuleiros lado a lado. Tabuleiro esquerdo: Frota do Jogador. Tabuleiro direito: Frota do Computador (inicialmente oculta).

## Regras de Jogo
- **Turnos:** Alternados. Jogador atira, depois computador atira.
- **Ação do Jogador:** Clique em uma casa no tabuleiro do computador.
- **Ação do Computador:** Escolhe uma casa aleatória no tabuleiro do jogador que ainda não foi atingida.

## Feedback de Ação
- **Acerto:** A casa atingida é marcada com um símbolo de acerto (ex: 'X').
- **Erro:** A casa atingida é marcada com um símbolo de erro (ex: 'O').
- **Afundamento:** Se um tiro acertar a última parte de um navio, o jogo exibe uma mensagem "Navio afundado!" e destaca as casas desse navio.

## Condição de Vitória/Derrota
- **Vitória:** Afundar todos os navios do computador.
- **Derrota:** Afundar todos os navios do jogador.
- **Anúncio:** Mensagem final com opção de "Reiniciar Jogo".

## O que Fica Fora Desta Versão
- Posicionamento manual da frota pelo jogador.
- Efeitos sonoros.
- Salvamento de placar ou estatísticas.
- IA adversária com estratégia.
- Modos de jogo multiplayer.
