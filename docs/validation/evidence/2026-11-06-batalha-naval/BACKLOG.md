# BACKLOG - Jogo de Batalha Naval

## Prioridade 1: Configuração Inicial do Jogo

- **Como** jogador, **quero** que o jogo inicialize com dois tabuleiros 10x10 (jogador e computador) **para** ter uma base visual para a batalha.
- **Critério de Aceite**:
  - [ ] Tabuleiro do jogador exibido com coordenadas (A-J, 1-10)
  - [ ] Tabuleiro do computador exibido com coordenadas
  - [ ] Both tabuleiros inicialmente ocultos (navios do computador não visíveis)

## Prioridade 2: Posicionamento Aleatório de Navios

- **Como** jogador, **quero** que os navios sejam posicionados aleatoriamente no tabuleiro do computador **para** garantir partidas imprevisíveis.
- **Critério de Aceite**:
  - [ ] Frota completa posicionada: porta-aviões (5), encouraçado (4), cruzador (3), submarino (3), destróier (2)
  - [ ] Navios posicionados horizontalmente ou verticalmente sem sobreposição
  - [ ] Navios do jogador posicionados aleatoriamente (para simulação)

## Prioridade 3: Mecânica de Tiros e Respostas

- **Como** jogador, **quero** clicar nas casas do tabuleiro do computador **para** disparar tiros e tentar acertar os navios inimigos.
- **Critério de Aceite**:
  - [ ] Clique em casa vazia do computador exibe "Água" (erro)
  - [ ] Clique em casa com navio exibe "Acerto"
  - [ ] Computador responde com tiro aleatório em casa não atingida do jogador
  - [ ] Tiros repetidos são ignorados

## Prioridade 4: Feedback de Acertos e Afundamentos

- **Como** jogador, **quero** receber feedback visual sobre acertos, erros e navios afundados **para** acompanhar o progresso da batalha.
- **Critério de Aceite**:
  - [ ] Casas acertadas marcadas com cor differente (ex: vermelho)
  - [ ] Casas erradas marcadas com cor differente (ex: azul)
  - [ ] Quando um navio é completamente afundado, exibe mensagem "Navio afundado!"

## Prioridade 5: Controle de Jogo e Vitória

- **Como** jogador, **quero** que o jogo announce vitória ou derrota quando todos os navios de um lado forem afundados **para** finalizar a partida.
- **Critério de Aceite**:
  - [ ] Mensagem de vitória quando todos os navios do computador forem afundados
  - [ ] Mensagem de derrota quando todos os navios do jogador forem afundados
  - [ ] Botão "Reiniciar Jogo" para iniciar nova partida

## Itens para Futuras Versões

- Som e efeitos sonoros
- Interface gráfica aprimorada com imagens de navios
- Modo multiplayer (dois jogadores)
- Estatísticas de jogo (precisão, etc.)
- Dificuldade ajustável (IA do computador com estratégias)
