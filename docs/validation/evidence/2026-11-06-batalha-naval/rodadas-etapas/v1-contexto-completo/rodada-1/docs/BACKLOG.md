# BACKLOG - Jogo Batalha Naval (TRC-20261107-DF4B93)

## MVP Prioritário

### US-001: Configuração Inicial do Tabuleiro
- **Como** jogador,
- **Quero** ver dois tabuleiros 10x10 (jogador e computador),
- **Para** ter a base visual do jogo.

**Critério de Aceite:**
- [ ] Tabuleiro do jogador exibido com coordenadas A1-J10
- [ ] Tabuleiro do computador exibido com coordenadas A1-J10
- [ ] Células vazias exibidas com cor neutra
- [ ] Layout responsivo para telas pequenas

---

### US-002: Posicionamento Aleatório de Navios
- **Como** jogador,
- **Quero** que os navios sejam posicionados aleatoriamente sem sobreposição,
- **Para** garantir partidas imprevisíveis.

**Critério de Aceite:**
- [ ] Porta-aviões (5) posicionado corretamente
- [ ] Encouraçado (4) posicionado corretamente
- [ ] Cruzador (3) posicionado corretamente
- [ ] Submarino (3) posicionado corretamente
- [ ] Destróier (2) posicionado corretamente
- [ ] Nenhum navio sobreposto
- [ ] Todos os navios dentro dos limites do tabuleiro

---

### US-003: Sistema de Ataque do Jogador
- **Como** jogador,
- **Quero** atacar o tabuleiro do computador ao clicar,
- **Para** danificar a frota inimiga.

**Critério de Aceite:**
- [ ] Clique em célula desbloqueada permite ataque
- [ ] Célula já atacada não permite novo ataque
- [ ] Acerto exibe cor de acerto
- [ ] Erro exibe cor de erro
- [ ] Áudio opcional para acerto/erro

---

### US-004: IA do Computador
- **Como** computador,
- **Quero** atacar aleatoriamente células não atingidas,
- **Para** desafiar o jogador.

**Critério de Aceite:**
- [ ] IA ataca após o jogador
- [ ] Ataque aleatório em célula não visitada
- [ ] Respeita células já atacadas
- [ ] Dificuldade equivalente ao jogador (aleatório puro)

---

### US-005: Detecção de Navio Afundado
- **Como** jogador,
- **Quero** saber quando um navio é afundado,
- **Para** acompanhar o progresso.

**Critério de Aceite:**
- [ ] Mensagem "Navio afundado!" exibida
- [ ] Todas as partes do navio marcadas como acertadas
- [ ] Identificação clara do navio afundado

---

### US-006: Controle de Vitória/Derrota
- **Como** jogador,
- **Quero** que o jogo termine quando todas as naves forem afundadas,
- **Para** finalizar a partida.

**Critério de Aceite:**
- [ ] Vitória exibida quando todos os navios inimigos afundados
- [ ] Derrota exibida quando todos os navios do jogador afundados
- [ ] Botão "Reiniciar Jogo" disponível
- [ ] Reinício limpa todos os estados

---

### US-007: Feedback Visual e Sonoro
- **Como** jogador,
- **Quero** receber feedback imediato de acerto/erro,
- **Para** melhorar a experiência.

**Critério de Aceite:**
- [ ] Cores distintas para acerto (ex: vermelho) e erro (ex: azul)
- [ ] Efeito sonoro opcional para acerto/erro
- [ ] Animação sutil ao clicar

---

## Itens para Futuras Versões

- Modo 2 jogadores (local multiplayer)
- Dificuldades variáveis (inteligência artificial)
- Estatísticas de partida (acertos, erros, precisão)
- Temas visuais alternativos
- Modo campal (tabuleiro maior)
- Histórico de partidas
- Interface de configuração de som
