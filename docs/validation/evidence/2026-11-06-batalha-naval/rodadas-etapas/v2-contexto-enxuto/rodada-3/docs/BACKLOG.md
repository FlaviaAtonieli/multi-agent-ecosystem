# BACKLOG MVP - Batalha Naval

## Histórias de Usuário (Ordem de Prioridade)

1. **Como jogador, quero visualizar o tabuleiro 10x10 para posicionar minha frota.**
   - Critério de aceite: Tabuleiro exibido com casas vazias, identificadas por coordenadas (A-J, 1-10).

2. **Como jogador, quero posicionar minha frota manualmente clicando nas casas.**
   - Critério de aceite: Clicar em uma casa altera sua cor para representar o navio, impedindo sobreposição.

3. **Como jogador, quero posicionar minha frota aleatoriamente.**
   - Critério de aceite: Botão "Posicionar Aleatoriamente" distribui os navios sem sobreposição e sem sair do tabuleiro.

4. **Como jogador, quero iniciar a partida após posicionar a frota.**
   - Critério de aceite: Botão "Iniciar Jogo" habilita o tabuleiro do computador e desativa a edição do meu tabuleiro.

5. **Como jogador, quero atacar o tabuleiro do computador clicando em casas não atingidas.**
   - Critério de aceite: Cada clique envia um tiro; casa já atingida fica desabilitada.

6. **Como jogador, quero receber feedback de acerto, erro e afundamento.**
   - Critério de aceite: Casa acerta exibe "Acerto!" e marca o navio; casa errada exibe "Água!"; quando um navio é totalmente afundado, exibe "Navio afundado!".

7. **Como computador, quero gerar uma frota aleatória sem sobreposição.**
   - Critério de aceite: A frota do computador é posicionada automaticamente no início da partida, respeitando as mesmas regras do jogador.

8. **Como computador, quero atacar aleatoriamente casas não atingidas do tabuleiro do jogador.**
   - Critério de aceite: O computador escolhe uma casa aleatória que ainda não foi atingida a cada rodada.

9. **Como jogador, quero ser notificado sobre vitória ou derrota.**
   - Critério de aceite: Quando toda a frota do adversário é afundada, exibe "Você venceu!"; quando minha frota é totalmente afundada, exibe "Você perdeu!".

10. **Como jogador, quero reiniciar a partida.**
    - Critério de aceite: Botão "Reiniciar" limpa ambos os tabuleiros e redefine o estado inicial.

## O que fica para depois (Backlog)
- Efeitos sonoros e animações visuais.
- Modo multiplayer (dois jogadores).
- Estatísticas de partida (acertos, erros, tempo).
- Temas visuais alternativos.
- IA adversária com estratégias (caçar navios).