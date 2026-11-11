# PLANO TÉCNICO ESTRUTURADO - Jogo Batalha Naval

## Análise de Domínio
- **Domínio:** Programação de Jogos
- **Tipo:** Jogo de tabuleiro para navegador (HTML5, CSS3, JavaScript puro)
- **Arquitetura:** Aplicação single-page, sem dependências externas
- **Público-alvo:** Usuários finais para validação do fluxo de trabalho

## Arquitetura do Sistema

### Estrutura de Arquivos
1. **index.html** - Estrutura básica, elementos principais e carregamento de scripts
2. **style.css** - Estilização completa, layout responsivo e feedbacks visuais
3. **game.js** - Lógica central do jogo, gerenciamento de estado e interações

### Componentes Principais
- Dois tabuleiros 10x10 (jogador e computador)
- Sistema de posicionamento de frota
- Motor de turnos alternados
- Sistema de feedback visual (acerto/erro/afundamento)
- Gerenciamento de estado de vitória/derrota

## Planejamento de Implementação

### Fase 1: Estrutura Básica (HTML/CSS)
1. Criar tabuleiros com IDs estáveis:
   - `player-board` para tabuleiro do jogador
   - `computer-board` para tabuleiro do computador
   - `status-message` para exibição de mensagens
   - `restart-button` para reiniciar jogo

2. Estilização:
   - Layout flexível para tabuleiros lado a lado
   - Células com hover effects
   - Cores de feedback: verde para acerto, vermelho para erro
   - Botão de reiniciar visível

### Fase 2: Lógica de Jogo (JavaScript)

#### 2.1 Posicionamento de Frota
```javascript
// Estrutura de dados:
const SHIPS = [
  { name: 'Porta-aviões', size: 5 },
  { name: 'Encouraçado', size: 4 },
  { name: 'Cruzador', size: 3 },
  { name: 'Submarino', size: 3 },
  { name: 'Destróier', size: 2 }
];

// Algoritmo de posicionamento:
function positionShips(board) {
  SHIPS.forEach(ship => {
    let placed = false;
    while (!placed) {
      const horizontal = Math.random() < 0.5;
      const row = Math.floor(Math.random() * 10);
      const col = Math.floor(Math.random() * 10);
      
      if (canPlaceShip(board, row, col, ship.size, horizontal)) {
        placeShip(board, row, col, ship.size, horizontal);
        placed = true;
      }
    }
  });
}
```

#### 2.2 Sistema de Turnos
- Jogador clica em célula do tabuleiro do computador
- Validação de jogada (se já foi atingida)
- Processamento do tiro (acerto/erro)
- Verificação de afundamento
- Turno automático do computador (posição aleatória não atingida)

#### 2.3 Feedback Visual
- Acerto: marcação 'X' em verde
- Erro: marcação 'O' em vermelho
- Afundamento: destaque especial no navio afundado
- Mensagens textuais no elemento de status

### Fase 3: Condições de Vitória
- Verificar se todos os navios do computador foram afundados
- Verificar se todos os navios do jogador foram afundados
- Exibir mensagem de vitória/derrota
- Habilitar botão de reiniciar

## Plano de Testes

### Testes Unitários
1. **Posicionamento:** Verificar que navios não se sobrepõem
2. **Turnos:** Validar alternância de turnos
3. **Feedback:** Confirmar marcas corretas para acerto/erro

### Testes de Integração
1. **Fluxo completo:** Jogar até o fim com simulações
2. **Casos de borda:** Tabuleiro cheio, múltiplos acertos no mesmo navio
3. **Recuperação de erro:** Reiniciar jogo e verificar estado limpo

## Critérios de Aceite
- [ ] Jogo carregável via index.html direto
- [ ] Tabuleiros 10x10 com todas as embarcações
- [ ] Jogadas alternadas funcionando
- [ ] Feedbacks visuais corretos
- [ ] Condições de vitória detectadas
- [ ] Reiniciar jogo restaura estado inicial

## Considerações Finais
- Performance: Otimizado para 100+ interações sem degradação
- Compatibilidade: Navegadores modernos (Chrome, Firefox, Edge)
- Acessibilidade: Suporte básico a teclado e contraste
- Expansibilidade: Estrutura permite adicionar novos navios ou modos