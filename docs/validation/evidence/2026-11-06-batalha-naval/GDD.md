# Game Design Document - Batalha Naval

## Visão Geral
Jogo de batalha naval para navegador, 1 contra 1 contra a IA. O objetivo é afundar todos os navios do adversário antes que o adversário afunde os seus.

## Regras Básicas
- Tabuleiro 10x10 para jogador e computador.
- Frota: 1 Porta-Aviões (5), 1 Encouraçado (4), 1 Cruzador (3), 1 Submarino (3), 1 Destróier (2).
- Navios posicionados horizontal ou verticalmente, sem sobreposição.
- Jogador e computador alternam turnos, começando pelo jogador.
- Cada tiro é em uma casa específica.

## Preparação
1. **Posicionamento da Frota do Jogador**: Aleatório, respeitando limites e sem sobreposição.
2. **Posicionamento da Frota do Computador**: Aleatório, respeitando limites e sem sobreposição.

## Turnos
1. **Turno do Jogador**: Jogador clica em uma casa no tabuleiro do computador.
   - Acerto: A casa é marcada como acertada.
   - Erro: A casa é marcada como errada.
   - Afundamento: Se o tiro acertar a última parte de um navio, o navio é considerado afundado.
2. **Turno do Computador**: Computador escolhe uma casa aleatória no tabuleiro do jogador que ainda não foi atingida.
   - Acerto, Erro e Afundamento seguem as mesmas regras.

## Feedback
- **Acerto**: Marcar a casa com uma cor distinta (ex: vermelho).
- **Erro**: Marcar a casa com uma cor distinta (ex: azul).
- **Afundamento**: Anunciar qual navio foi afundado.

## Condição de Vitória e Derrota
- **Vitória**: Jogador afunda todos os navios do computador.
- **Derrota**: Computador afunda todos os navios do jogador.
- Ao final, exibir mensagem de vitória/derrota e opção de reiniciar.

## Fora do Escopo (Primeira Versão)
- Efeitos sonoros.
- Animações visuais.
- Modo multiplayer.
- Dificuldades variáveis da IA.
- Visualização do tabuleiro inimigo antes do jogo.
