// Batalha Naval - Jogo Completo
// Versão: 1.0

// Constantes do jogo
const BOARD_SIZE = 10;
const SHIPS = [
  { name: 'Porta-aviões', size: 5 },
  { name: 'Encouraçado', size: 4 },
  { name: 'Cruzador', size: 3 },
  { name: 'Submarino', size: 3 },
  { name: 'Destróier', size: 2 }
];

// Estado do jogo
let gameState = {
  playerBoard: [],
  computerBoard: [],
  playerShips: [],
  computerShips: [],
  playerTurn: true,
  gameOver: false,
  playerHits: new Set(),
  computerHits: new Set(),
  playerMisses: new Set(),
  computerMisses: new Set()
};

// Inicializar jogo
function initGame() {
  // Limpar estado anterior
  gameState.playerBoard = createEmptyBoard();
  gameState.computerBoard = createEmptyBoard();
  gameState.playerShips = [];
  gameState.computerShips = [];
  gameState.playerTurn = true;
  gameState.gameOver = false;
  gameState.playerHits.clear();
  gameState.computerHits.clear();
  gameState.playerMisses.clear();
  gameState.computerMisses.clear();
  
  // Posicionar navios
  positionShips(gameState.playerBoard, gameState.playerShips, true);
  positionShips(gameState.computerBoard, gameState.computerShips, false);
  
  // Renderizar tabuleiros
  renderBoard('player-board', gameState.playerBoard, false);
  renderBoard('computer-board', gameState.computerBoard, true);
  
  // Atualizar status
  updateStatus('Sua vez! Clique no tabuleiro do computador para atirar.');
}

// Criar tabuleiro vazio
function createEmptyBoard() {
  const board = [];
  for (let row = 0; row < BOARD_SIZE; row++) {
    board[row] = [];
    for (let col = 0; col < BOARD_SIZE; col++) {
      board[row][col] = { ship: null, hit: false };
    }
  }
  return board;
}

// Posicionar navios aleatoriamente
function positionShips(board, ships, isPlayer) {
  SHIPS.forEach(ship => {
    let placed = false;
    while (!placed) {
      const horizontal = Math.random() < 0.5;
      const row = Math.floor(Math.random() * BOARD_SIZE);
      const col = Math.floor(Math.random() * BOARD_SIZE);
      
      if (canPlaceShip(board, row, col, ship.size, horizontal)) {
        placeShip(board, row, col, ship.size, horizontal, ship, ships);
        placed = true;
      }
    }
  });
}

// Verificar se pode posicionar navio
function canPlaceShip(board, row, col, size, horizontal) {
  for (let i = 0; i < size; i++) {
    const currentRow = horizontal ? row : row + i;
    const currentCol = horizontal ? col + i : col;
    
    if (currentRow >= BOARD_SIZE || currentCol >= BOARD_SIZE) {
      return false;
    }
    
    if (board[currentRow][currentCol].ship !== null) {
      return false;
    }
  }
  return true;
}

// Posicionar navio no tabuleiro
function placeShip(board, row, col, size, horizontal, ship, ships) {
  const shipCells = [];
  
  for (let i = 0; i < size; i++) {
    const currentRow = horizontal ? row : row + i;
    const currentCol = horizontal ? col + i : col;
    
    board[currentRow][currentCol].ship = ship;
    shipCells.push({ row: currentRow, col: currentCol });
  }
  
  ships.push({
    ...ship,
    cells: shipCells,
    hits: new Set()
  });
}

// Renderizar tabuleiro
function renderBoard(boardId, board, isComputer) {
  const boardElement = document.getElementById(boardId);
  boardElement.innerHTML = '';
  
  for (let row = 0; row < BOARD_SIZE; row++) {
    for (let col = 0; col < BOARD_SIZE; col++) {
      const cell = document.createElement('div');
      cell.className = 'cell';
      cell.dataset.row = row;
      cell.dataset.col = col;
      
      // Mostrar navios do jogador
      if (!isComputer && board[row][col].ship) {
        cell.classList.add('player-ship');
      }
      
      // Efeito de acerto/erro
      if (isComputer && (gameState.playerHits.has(`${row}-${col}`))) {
        cell.classList.add('hit');
      } else if (isComputer && (gameState.playerMisses.has(`${row}-${col}`))) {
        cell.classList.add('miss');
      }
      
      if (!isComputer && (gameState.computerHits.has(`${row}-${col}`))) {
        cell.classList.add('hit');
      } else if (!isComputer && (gameState.computerMisses.has(`${row}-${col}`))) {
        cell.classList.add('miss');
      }
      
      // Adicionar evento de clique
      if (isComputer && gameState.playerTurn && !gameState.gameOver) {
        cell.addEventListener('click', () => handlePlayerAttack(row, col));
      }
      
      boardElement.appendChild(cell);
    }
  }
}

// Processar ataque do jogador
function handlePlayerAttack(row, col) {
  const cellKey = `${row}-${col}`;
  
  // Verificar se já atacou
  if (gameState.playerHits.has(cellKey) || gameState.playerMisses.has(cellKey)) {
    return;
  }
  
  const target = gameState.computerBoard[row][col];
  
  if (target.ship) {
    // Acerto
    gameState.playerHits.add(cellKey);
    target.ship.hits.add(cellKey);
    
    updateStatus('ACERTO!');
    
    // Verificar se o navio foi afundado
    if (target.ship.hits.size === target.ship.size) {
      updateStatus(`ACERTO! Navio ${target.ship.name} afundado!`);
      markSunkShip(gameState.computerBoard, target.ship);
    }
    
    // Verificar vitória
    if (checkVictory('computer')) {
      endGame(true);
      return;
    }
  } else {
    // Erro
    gameState.playerMisses.add(cellKey);
    updateStatus('Errou!');
  }
  
  // Atualizar tabuleiro
  renderBoard('computer-board', gameState.computerBoard, true);
  
  // Turno do computador
  gameState.playerTurn = false;
  setTimeout(computerAttack, 1000);
}

// Ataque do computador
function computerAttack() {
  if (gameState.gameOver) return;
  
  let attackRow, attackCol, cellKey;
  
  // Escolher um ataque válido
  do {
    attackRow = Math.floor(Math.random() * BOARD_SIZE);
    attackCol = Math.floor(Math.random() * BOARD_SIZE);
    cellKey = `${attackRow}-${attackCol}`;
  } while (gameState.computerHits.has(cellKey) || gameState.computerMisses.has(cellKey));
  
  const target = gameState.playerBoard[attackRow][attackCol];
  
  if (target.ship) {
    // Acerto
    gameState.computerHits.add(cellKey);
    target.ship.hits.add(cellKey);
    
    updateStatus('Computador acertou!');
    
    // Verificar se o navio foi afundado
    if (target.ship.hits.size === target.ship.size) {
      updateStatus(`Computador afundou seu ${target.ship.name}!`);
      markSunkShip(gameState.playerBoard, target.ship);
    }
    
    // Verificar derrota
    if (checkVictory('player')) {
      endGame(false);
      return;
    }
  } else {
    // Erro
    gameState.computerMisses.add(cellKey);
    updateStatus('Computador errou!');
  }
  
  // Atualizar tabuleiro
  renderBoard('player-board', gameState.playerBoard, false);
  
  // Voltar para o jogador
  gameState.playerTurn = true;
  updateStatus('Sua vez! Clique no tabuleiro do computador para atirar.');
}

// Marcar navio afundado
function markSunkShip(board, ship) {
  ship.cells.forEach(cell => {
    const cellElement = document.querySelector(
      `#player-board [data-row="${cell.row}"][data-col="${cell.col}"]` +
      `, #computer-board [data-row="${cell.row}"][data-col="${cell.col}"]`
    );
    if (cellElement) {
      cellElement.classList.add('sunk');
    }
  });
}

// Verificar vitória
function checkVictory(opponent) {
  if (opponent === 'computer') {
    // Jogador venceu se todos os navios do computador foram afundados
    return gameState.computerShips.every(ship => ship.hits.size === ship.size);
  } else {
    // Computador venceu se todos os navios do jogador foram afundados
    return gameState.playerShips.every(ship => ship.hits.size === ship.size);
  }
}

// Finalizar jogo
function endGame(playerWon) {
  gameState.gameOver = true;
  
  const statusMessage = document.getElementById('status-message');
  if (playerWon) {
    statusMessage.textContent = 'Parabéns! Você venceu!';
    statusMessage.classList.add('victory');
  } else {
    statusMessage.textContent = 'Game Over! Computador venceu!';
    statusMessage.classList.add('defeat');
  }
}

// Atualizar mensagem de status
function updateStatus(message) {
  const statusMessage = document.getElementById('status-message');
  statusMessage.textContent = message;
  statusMessage.classList.remove('victory', 'defeat');
}

// Inicializar quando a página carrega
window.addEventListener('DOMContentLoaded', () => {
  initGame();
  
  // Configurar botão de reiniciar
  document.getElementById('restart-btn').addEventListener('click', () => {
    initGame();
  });
});