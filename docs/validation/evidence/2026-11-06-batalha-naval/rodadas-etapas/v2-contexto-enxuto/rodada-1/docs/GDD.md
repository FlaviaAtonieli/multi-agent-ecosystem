# Game Design Document - Batalha Naval

## Regras
- Tabuleiro 10x10 para jogador e para o computador.
- Frota: porta-aviões (5), encouraçado (4), cruzador (3), submarino (3) e destróier (2).
- Posicionamento aleatório sem sobreposição.

## Preparação
- Cada lado posiciona sua frota aleatoriamente.
- O jogo começa com o jogador.

## Turnos
- Jogador clica em uma casa no tabuleiro do computador.
- Computador responde com um tiro aleatório em casa ainda não atingida.

## Feedback
- Acerto: cor verde, texto "Acerto!".
- Erro: cor vermelha, texto "Errou!".
- Afundamento: quando todos os segmentos de um navio são atingidos, mensagem "Navio afundado!".

## Vitória e Derrota
- Vitória: todos os navios do computador afundados.
- Derrota: todos os navios do jogador afundados.
- Opção de reiniciar ao final.

## Fora desta versão
- Som e efeitos visuais avançados.
- Modo multiplayer.
- IA estratégica.
- Salvamento de jogo.