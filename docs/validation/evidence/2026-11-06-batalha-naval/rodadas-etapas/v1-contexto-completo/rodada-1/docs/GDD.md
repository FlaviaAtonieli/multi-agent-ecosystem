# Game Design Document - Batalha Naval

## Regras
- Tabuleiro 10x10 para jogador e computador.
- Frota: porta-aviões (5), encouraçado (4), cruzador (3), submarino (3), destróier (2).
- Posicionamento aleatório sem sobreposição.
- Jogador atira clicando no tabuleiro do computador.
- Computador responde com tiro aleatório em casa não atingida.
- Acerto, erro, afundamento são announced.

## Preparação
- Gerar tabuleiro do computador com frota aleatória.
- Tabuleiro do jogador vazio, ready for input.

## Turnos
- Turno do jogador: clique na casa, verificar acerto/erro.
- Turno do computador: escolher casa aleatória não atingida, verificar acerto/erro.

## Feedback de Acerto, Erro e Afundamento
- Acerto: marcação de cor, se afundar navio, message.
- Erro: marcação diferente, message.
- Afundamento: quando todos os segmentos de um navio são atingidos, announce.

## Condição de Vitória e Derrota
- Vitória: todos os navios do computador afundados.
- Derrota: todos os navios do jogador afundados.
- Anunciar vitória/derrota e opção de reiniciar.

## O que fica fora desta primeira versão
- Sons e efeitos visuais.
- Modo multiplayer.
- História ou níveis.
- Estatísticas.