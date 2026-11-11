# Game Design Document - Batalha Naval

## 1. Visão Geral
- Jogo single-player contra computador.
- Tabuleiro 10x10 para jogador e inimigo.
- Frota: porta-aviões (5), encouraçado (4), cruzador (3), submarino (3), destróier (2).

## 2. Preparação
- Gerar tabuleiro do jogador: posicionar navios aleatoriamente sem sobreposição.
- Gerar tabuleiro do computador: mesmo processo.
- Cada navio ocupa células adjacentes horizontalmente ou verticalmente.

## 3. Turnos
- Jogador clica em uma célula no tabuleiro do computador.
- Verificar acerto/erro.
- Computador escolhe uma célula aleatória não atingida no tabuleiro do jogador e atira.
- Atualizar feedback.

## 4. Feedback
- Acerto: mudar cor da célula, exibir mensagem "Acerto!".
- Erro: mudar cor, exibir "Água!".
- Afundamento: quando todos os segmentos de um navio são atingidos, exibir "Navio X afundado!".
- Vitória: todos os navios do computador afundados.
- Derrota: todos os navios do jogador afundados.

## 5. Condição de Vitória/Derrota
- Vitória se todos os navios inimigos forem afundados.
- Derrota se todos os navios do jogador forem afundados.
- Exibir mensagem final e botão "Reiniciar".

## 6. O que fica fora desta primeira versão
- Som e efeitos sonoros.
- Interface gráfica avançada (animações, sprites).
- Modo multiplayer.
- Estratégia de IA mais sofisticada (busca de navios).
- Persistência de placar.