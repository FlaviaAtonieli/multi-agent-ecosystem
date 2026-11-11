// Batalha Naval - Jogo Completo
// Criado para Validação do Fluxo do Time de Jogos

// Configuração do jogo
const BOARD_SIZE = 10;
const FLEET = [
    { name: 'Porta-aviões', size: 5 },
    { name: 'Encouraçado', size: 4 },
    { name: 'Cruzador', size: 3 },
    { name: 'Submarino', size: 3 },
    { name: 'Destróier', size: 2 }
];

// Estado do jogo
let playerBoard = [];
let computerBoard = [];
let playerShots = new Set();
let computerShots = new Set();
let gameOver = false;
let playerTurn = true;

// Inicializar jogo
function initGame() {
    playerBoard = createBoard();
    computerBoard = createBoard();
    
    // Posicionar navios
    placeShips(playerBoard, FLEET);
    placeShips(computerBoard, FLEET);
    
    // Renderizar tabuleiros
    renderBoard('player-board', playerBoard, false);
    renderBoard('computer-board', computerBoard, true);
    
    // Resetear estado
    playerShots.clear();
    computerShots.clear();
    gameOver = false;
    playerTurn = true;
    
    updateStatus('Clique nas casas do tabuleiro inimigo para atirar!', 'normal');
}

// Criar tabuleiro vazio
function createBoard() {
    const board = [];
    for (let i = 0; i < BOARD_SIZE; i++) {
        board[i] = [];
        for (let j = 0; j < BOARD_SIZE; j++) {
            board[i][j] = { ship: null, hit: false };
        }
    }
    return board;
}

// Posicionar navios aleatoriamente
function placeShips(board, fleet) {
    fleet.forEach(ship => {
        let placed = false;
        while (!placed) {
            const horizontal = Math.random() < 0.5;
            const row = Math.floor(Math.random() * BOARD_SIZE);
            const col = Math.floor(Math.random() * BOARD_SIZE);
            
            if (canPlaceShip(board, row, col, ship.size, horizontal)) {
                // Posicionar navio
                for (let i = 0; i < ship.size; i++) {
                    const currentRow = horizontal ? row : row + i;
                    const currentCol = horizontal ? col + i : col;
                    board[currentRow][currentCol].ship = ship.name;
                }
                placed = true;
            }
        }
    });
}

// Verificar se navio pode ser posicionado
function canPlaceShip(board, row, col, size, horizontal) {
    for (let i = 0; i < size; i++) {
        const currentRow = horizontal ? row : row + i;
        const currentCol = horizontal ? col + i : col;
        
        // Verificar limites
        if (currentRow >= BOARD_SIZE || currentCol >= BOARD_SIZE) {
            return false;
        }
        
        // Verificar sobreposição
        if (board[currentRow][currentCol].ship !== null) {
            return false;
        }
    }
    return true;
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
            
            // Mostrar navios apenas no tabuleiro do jogador
            if (!isComputer && board[row][col].ship) {
                cell.classList.add('ship');
            }
            
            // Mostrar acertos e erros
            if (board[row][col].hit) {
                if (board[row][col].ship) {
                    cell.classList.add('hit');
                    cell.textContent = 'X';
                } else {
                    cell.classList.add('miss');
                    cell.textContent = '·';
                }
            }
            
            // Adicionar evento de clique apenas no tabuleiro do computador
            if (isComputer && !board[row][col].hit && !gameOver) {
                cell.addEventListener('click', () => handlePlayerShot(row, col));
            }
            
            boardElement.appendChild(cell);
        }
    }
}

// Processar tiro do jogador
function handlePlayerShot(row, col) {
    if (gameOver || !playerTurn) return;
    
    const shotKey = `${row}-${col}`;
    if (playerShots.has(shotKey)) return;
    
    playerShots.add(shotKey);
    computerBoard[row][col].hit = true;
    
    const cell = document.querySelector(`#computer-board .cell[data-row="${row}"][data-col="${col}"]`);
    
    if (computerBoard[row][col].ship) {
        cell.classList.add('hit');
        cell.textContent = 'X';
        updateStatus('ACERTO! Continue atirando.', 'hit');
        
        // Verificar se o navio foi afundado
        if (isShipSunk(computerBoard, computerBoard[row][col].ship)) {
            updateStatus(`Navio ${computerBoard[row][col].ship} afundado!`, 'sunk');
        }
        
        // Verificar vitória
        if (checkWin(computerBoard)) {
            endGame(true);
            return;
        }
    } else {
        cell.classList.add('miss');
        cell.textContent = '·';
        updateStatus('ERRO! Vez do computador.', 'miss');
        playerTurn = false;
        
        // Computador joga após um pequeno delay
        setTimeout(computerTurn, 1000);
    }
    
    renderBoard('computer-board', computerBoard, true);
}

// Verificar se um navio foi afundado
function isShipSunk(board, shipName) {
    for (let row = 0; row < BOARD_SIZE; row++) {
        for (let col = 0; col < BOARD_SIZE; col++) {
            if (board[row][col].ship === shipName && !board[row][col].hit) {
                return false;
            }
        }
    }
    return true;
}

// Verificar vitória
function checkWin(board) {
    for (let row = 0; row < BOARD_SIZE; row++) {
        for (let col = 0; col < BOARD_SIZE; col++) {
            if (board[row][col].ship && !board[row][col].hit) {
                return false;
            }
        }
    }
    return true;
}

// Turno do computador
function computerTurn() {
    if (gameOver) return;
    
    // Escolher uma casa aleatória que não foi atingida
    let row, col, shotKey;
    do {
        row = Math.floor(Math.random() * BOARD_SIZE);
        col = Math.floor(Math.random() * BOARD_SIZE);
        shotKey = `${row}-${col}`;
    } while (computerShots.has(shotKey));
    
    computerShots.add(shotKey);
    playerBoard[row][col].hit = true;
    
    const cell = document.querySelector(`#player-board .cell[data-row="${row}"][data-col="${col}"]`);
    
    if (playerBoard[row][col].ship) {
        cell.classList.add('hit');
        cell.textContent = 'X';
        updateStatus('Computador acertou seu navio!', 'hit');
        
        // Verificar se o navio foi afundado
        if (isShipSunk(playerBoard, playerBoard[row][col].ship)) {
            updateStatus(`Seu navio ${playerBoard[row][col].ship} foi afundado!`, 'sunk');
        }
        
        // Verificar derrota
        if (checkWin(playerBoard)) {
            endGame(false);
            return;
        }
        
        // Computador atira novamente se acertar
        setTimeout(computerTurn, 1000);
    } else {
        cell.classList.add('miss');
        cell.textContent = '·';
        updateStatus('Computador errou! Sua vez.', 'miss');
        playerTurn = true;
    }
    
    renderBoard('player-board', playerBoard, false);
}

// Finalizar jogo
function endGame(playerWon) {
    gameOver = true;
    
    if (playerWon) {
        updateStatus('PARABÉNS! Você venceu!', 'win');
    } else {
        updateStatus('GAME OVER! Todos os seus navios foram afundados.', 'lose');
    }
}

// Atualizar mensagem de status
function updateStatus(message, type) {
    const statusElement = document.getElementById('status-message');
    statusElement.textContent = message;
    statusElement.className = `status-message ${type}`;
}

// Reiniciar jogo
function restartGame() {
    initGame();
}

// Inicializar quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', () => {
    initGame();
    
    // Adicionar evento de reiniciar
    document.getElementById('restart-button').addEventListener('click', restartGame);
});