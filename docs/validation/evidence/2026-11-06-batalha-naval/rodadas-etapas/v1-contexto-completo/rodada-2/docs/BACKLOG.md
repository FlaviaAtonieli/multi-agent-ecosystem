# Backlog - Jogo Batalha Naval

## Prioridade 1 (MVP)

### US-001: Exibir tabuleiro do jogador
- **Como** jogador
- **Quero** visualizar um tabuleiro 10x10 com minhas embarcações posicionadas
- **Para** que eu possa entender minha disposição defensiva
- **Critério de aceite**:
  - O tabuleiro é exibido com 10 linhas e 10 colunas
  - Cada célula mostra o estado (água, navio, acerto, erro)
  - As posições dos navios são marcadas visualmente

### US-002: Exibir tabuleiro do computador
- **Como** jogador
- **Quero** visualizar o tabuleiro do computador 10x10
- **Para** que eu possa atirar nas posições inimigas
- **Critério de aceite**:
  - O tabuleiro é exibido com 10 linhas e 10 colunas
  - Inicialmente todas as células estão ocultas (água)
  - Cada célula é clicável

### US-003: Posicionar frota aleatoriamente
- **Como** sistema
- **Quero** posicioner cada navio em posições aleatórias sem sobreposição
- **Para** garantir que o jogo comece com uma frota válida
- **Critério de aceite**:
  - Porta-aviões (5), Encouraçado (4), Cruzador (3), Submarino (3), Destroier (2) são posicionados
  - Nenhum navio se sobrepõe
  - Os navios são colocados horizontalmente ou verticalmente

### US-004: Jogador atira no computador
- **Como** jogador
- **Quero** clicar em uma célula do tabuleiro do computador
- **Para** tentar acertar os navios inimigos
- **Critério de aceite**:
  - Ao clicar, a célula é marcada como acerto ou erro
  - Se houver navio, a célula muda de cor para acerto
  - Se não houver navio, muda para erro
  - Células já atingidas não podem ser clicadas novamente

### US-005: Computador atira no jogador
- **Como** sistema
- **Quero** escolher uma célula aleatória no tabuleiro do jogador ainda não atingida
- **Para** simular um ataque inimigo
- **Critério de aceite**:
  - Após o jogador atirar, o computador seleciona uma célula aleatória
  - A célula é marcada como acerto ou erro no tabuleiro do jogador
  - O computador não atira em células já atingidas

### US-006: Exibir feedback de acerto/erro/afundamento
- **Como** jogador
- **Quero** receber mensagens claras sobre o resultado de cada tiro
- **Para** saber se acertei ou errei, e se algum navio foi afundado
- **Critério de aceite**:
  - Mensagem de "Acerto!" ou "Errou!" é exibida
  - Se um navio for afundado, é exibido "Navio X afundado!"
  - O estado visual das células reflete acerto/erro

### US-007: Detectar vitória ou derrota
- **Como** sistema
- **Quero** verificar quando todos os navios de um lado são afundados
- **Para** anunciar o resultado do jogo
- **Critério de aceite**:
  - Quando todos os navios do computador forem afundados, exibe "Você venceu!"
  - Quando todos os navios do jogador forem afundados, exibe "Você perdeu!"
  - O jogo para automaticamente

### US-008: Reiniciar jogo
- **Como** jogador
- **Quero** poder reiniciar o jogo após o termino
- **Para** jogar novamente sem recarregar a página
- **Critério de aceite**:
  - Botão "Reiniciar" ou similar é exibido após o fim do jogo
  - Ao clicar, os tabuleiros são limpos e novas frotas são posicionadas
  - O jogo recomeça do zero

## Prioridade 2 (Melhorias)

- Efeitos sonoros de acerto/erro
- Animações de explosão
- Histórico de tiros
- Modo dois jogadores
- Configuração de dificuldade
- Tema visual personalizável