# BACKLOG - Jogo de Batalha Naval

## MVP (Produtível Mínimo Viable)

### 1. Configuração Inicial do Projeto
- **Como** desenvolvedor, **quero** ter a estrutura básica de arquivos (index.html, style.css, game.js) para que o jogo possa ser carregado no navegador.
- **Critério de Aceite**:
  - index.html carregado sem erros no navegador.
  - style.css aplicado, exibindo um tabuleiro vazio.
  - game.js carregado, podendo ser executado no console.

### 2. Geração da Frota Aleatória
- **Como** jogador, **quero** que a frota do computador seja posicionada aleatoriamente sem sobreposição para que o jogo seja imprevisível.
- **Critério de Aceite**:
  - A frota contém todos os navios: porta-aviões (5), encouraçado (4), cruzador (3), submarino (3), destróier (2).
  - Nenhum navio se sobrepõe a outro.
  - A posição é regenerada ao reiniciar o jogo.

### 3. Interação do Jogador (Ataque)
- **Como** jogador, **quero** clicar nas casas do tabuleiro do computador para atacar, recebendo feedback de acerto/erro.
- **Critério de Aceite**:
  - Ao clicar em uma casa não atacada, o jogo exibe "Acerto" ou "Água".
  - Casas já atacadas não podem ser clicadas novamente.
  - O tabuleiro visualiza os ataques com cores distintas.

### 4. Resposta do Computador
- **Como** jogador, **quero** que o computador ataque de forma aleatória em casas não atingidas para que haja desafio.
- **Critério de Aceite**:
  - Após o ataque do jogador, o computador escolhe uma casa aleatória no tabuleiro do jogador.
  - O jogo exibe o resultado do ataque do computador (acerto/erro).

### 5. Verificação de Navios Afundados
- **Como** jogador, **quero** ser notificado quando um navio é completamente afundado para que eu saiba minha progressão.
- **Critério de Aceite**:
  - Quando todos os segmentos de um navio são atingidos, o jogo exibe "Navio afundado: [Nome]".

### 6. Condição de Vitória/Derrota
- **Como** jogador, **quero** que o jogo anuncie a vitória ou derrota quando todos os navios de um lado forem afundados.
- **Critério de Aceite**:
  - Se todos os navios do computador forem afundados, exibe "Você venceu!".
  - Se todos os navios do jogador forem afundados, exibe "Você perdeu!".
  - O jogo para de aceitar mais ataques após o fim.

### 7. Reiniciar Jogo
- **Como** jogador, **quero** reiniciar o jogo a qualquer momento após a vitória ou derrota para que eu possa jogar novamente.
- **Critério de Aceite**:
  - Botão "Reiniciar" ou similar reinicia o jogo, gerando nova frota e limpando o tabuleiro.

## Funcionalidades para Futuras Versões (Fora do MVP)
- Placar de vitórias/derrotas.
- Dificuldade ajustável (computador com estratégias).
- Modo dois jogadores.
- Animações visuais e sons.
- Persistência de jogo (localStorage).
- Validação de positioning manual do jogador.
