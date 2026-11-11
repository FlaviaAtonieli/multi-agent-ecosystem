# BACKLOG - Jogo de Batalha Naval (TRC-20261107-F0E19A)

## MVP (Prioridade Máxima)

### US-01: Configuração Inicial do Tabuleiro
- **Como** jogador
- **Quero** ver o tabuleiro 10x10
- **Para** ter uma base visual para o jogo

**Critério de Aceite:**
- [ ] O tabuleiro do jogador é exibido corretamente com 10 linhas e 10 colunas.
- [ ] Cada célula tem um identificador único (ex: A1, B2).
- [ ] O tabuleiro do computador é exibido com as mesmas dimensões, mas as posições dos navios são ocultas.

---

### US-02: Posicionamento Aleatório da Frota
- **Como** sistema
- **Quero** posiciona automaticamente a frota do computador (Porta-aviões, Encouraçado, Cruzador, Submarino, Destróier)
- **Para** evitar intervenção manual e garantir que não há sobreposição

**Critério de Aceite:**
- [ ] A frota é posicionada de forma aleatória no tabuleiro do computador.
- [ ] Nenhum navio se sobrepõe a outro.
- [ ] Todos os navios cabem dentro do tabuleiro 10x10.

---

### US-03: Mecânica de Ataque do Jogador
- **Como** jogador
- **Quero** clicar em uma célula do tabuleiro do computador
- **Para** disparar um tiro e verificar o resultado

**Critério de Aceite:**
- [ ] Ao clicar em uma célula não atingida, o sistema marca um "erro" (ex: cor azul).
- [ ] Se houver um navio, marca um "acerto" (ex: cor vermelha).
- [ ] Células já atingidas não podem ser clicadas novamente.

---

### US-04: Resposta do Computador
- **Como** sistema
- **Quero** gerar um tiro aleatório no tabuleiro do jogador após a ação do jogador
- **Para** simular a jogada do adversário

**Critério de Aceite:**
- [ ] O computador escolhe uma célula aleatória que ainda não foi atingida.
- [ ] O resultado do tiro do computador (acerto/erro) é exibido visualmente no tabuleiro do jogador.
- [ ] Se um navio for atingido, o sistema notifica que um navio foi atingido.

---

### US-05: Controle de Danos e Afundamento
- **Como** jogador
- **Quero** receber feedback quando um navio for completamente afundado
- **Para** entender o progresso da batalha

**Critério de Aceite:**
- [ ] O sistema rastreia os acertos em cada navio.
- [ ] Quando todos os segmentos de um navio forem atingidos, uma mensagem de "Navio afundado" é exibida.
- [ ] O visual do navio no tabuleiro reflete o status de afundamento (opcional no MVP, mas a lógica deve estar lá).

---

### US-06: Condição de Vitória e Derrota
- **Como** jogador
- **Quero** saber quando o jogo terminar
- **Para** ver se venci ou perdi

**Critério de Aceite:**
- [ ] O jogo termina quando todos os navios do computador forem afundados (Vitória).
- [ ] O jogo termina quando todos os navios do jogador forem afundados (Derrota).
- [ ] Uma mensagem clara de "Vitória" ou "Derrota" é exibida ao final.

---

### US-07: Reiniciar Jogo
- **Como** jogador
- **Quero** poder reiniciar o jogo após o fim da partida
- **Para** jogar novamente sem recarregar a página

**Critério de Aceite:**
- [ ] Existe um botão visível de "Reiniciar Jogo".
- [ ] Ao clicar, o tabuleiro é limpo, a frota do computador é reposicionada aleatoriamente e o jogo recomeça.

---

## Para Depois (Backlog)

- Efeitos sonoros de acerto/erro/afundamento.
- Animações visuais de explosão.
- Contador de tiros e placar.
- Modo de dificuldade (Fácil, Médio, Difícil).
- Salvamento de jogo (Local Storage).
- Temas visuais alternativos.
- Suporte a mobile (toque).
- Multijogador (dois jogadores no mesmo tabuleiro).
- Estatísticas de jogadas.

---

## Arquivos Técnicos Propostos (Entregas Futuras)

- `index.html`: Estrutura básica, containers dos tabuleiros, botões de controle.
- `style.css`: Estilização dos tabuleiros, células, mensagens e layout responsivo (básico).
- `game.js`: Lógica principal de jogo, gerenciamento de estado, IA do computador e manipulação de eventos.
- `README.md`: Documentação de como executar e estrutura do código.

---

*Nota: O código-fonte será gerado a partir da implementação dessas histórias de usuário.*