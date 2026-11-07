// Definição dos navios
const ships = [
    { name: 'Porta-aviões', size: 5 },
    { name: 'Encouraçado', size: 4 },
    { name: 'Cruzador', size: 3 },
    { name: 'Submarino', size: 3 },
    { name: 'Destróier', size: 2 }
];

// Estado do jogo
let playerBoard = [];
let computerBoard = [];
let playerShips = [];
let computerShips = [];
let gameOver = false;

// Inicializar jogo
function initGame() {
    playerBoard = createBoard();
    computerBoard = createBoard();
    playerShips = [];
    computerShips = [];
    gameOver = false;

    // Posicionar navios do jogador (visíveis)
    positionShips(playerBoard, playerShips, true);
    // Posicionar navios do computador (ocultos)
    positionShips(computerBoard, computerShips, false);

    renderBoards();
    document.getElementById('status-message').textContent = 'Clique nas casas do tabuleiro do computador para atirar!';
    document.getElementById('restart-button').style.display = 'none';
}

// Criar tabuleiro 10x10
function createBoard() {
    const board = [];
    for (let i = 0; i < 10; i++) {
        board[i] = [];
        for (let j = 0; j < 10; j++) {
            board[i][j] = { ship: null, hit: false };
        }
    }
    return board;
}

// Posicionar navios aleatoriamente
function positionShips(board, shipsList, isVisible) {
    ships.forEach(ship => {
        let placed = false;
        while (!placed) {
            const direction = Math.random() < 0.5 ? 'horizontal' : 'vertical';
            const row = Math.floor(Math.random() * 10);
            const col = Math.floor(Math.random() * 10);

            if (canPlaceShip(board, row, col, ship.size, direction)) {
                placeShip(board, row, col, ship.size, direction, ship, shipsList);
                placed = true;
            }
        }
    });
}

// Verificar se pode posicionar navio
function canPlaceShip(board, row, col, size, direction) {
    for (let i = 0; i < size; i++) {
        const r = direction === 'horizontal' ? row : row + i;
        const c = direction === 'horizontal' ? col + i : col;

        if (r < 0 || r >= 10 || c < 0 || c >= 10) return false;
        if (board[r][c].ship !== null) return false;
    }
    return true;
}

// Posicionar navio no tabuleiro
function placeShip(board, row, col, size, direction, shipInfo, shipsList) {
    const shipCells = [];
    for (let i = 0; i < size; i++) {
        const r = direction === 'horizontal' ? row : row + i;
        const c = direction === 'horizontal' ? col + i : col;
        board[r][c].ship = shipInfo;
        shipCells.push({ row: r, col: c });
    }
    shipsList.push({ ...shipInfo, cells: shipCells, hits: 0 });
}

// Renderizar tabuleiros
function renderBoards() {
    const playerBoardElement = document.getElementById('player-board');
    const computerBoardElement = document.getElementById('computer-board');

    playerBoardElement.innerHTML = '';
    computerBoardElement.innerHTML = '';

    // Renderizar tabuleiro do jogador
    for (let i = 0; i < 10; i++) {
        for (let j = 0; j < 10; j++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            if (playerBoard[i][j].ship) {
                cell.classList.add('ship');
            }
            if (playerBoard[i][j].hit) {
                cell.classList.add('hit');
            }
            cell.dataset.row = i;
            cell.dataset.col = j;
            playerBoardElement.appendChild(cell);
        }
    }

    // Renderizar tabuleiro do computador
    for (let i = 0; i < 10; i++) {
        for (let j = 0; j < 10; j++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            if (computerBoard[i][j].hit) {
                if (computerBoard[i][j].ship) {
                    cell.classList.add('hit');
                } else {
                    cell.classList.add('miss');
                }
            }
            cell.dataset.row = i;
            cell.dataset.col = j;
            cell.addEventListener('click', handlePlayerAttack);
            computerBoardElement.appendChild(cell);
        }
    }
}

// Tratar ataque do jogador
function handlePlayerAttack(event) {
    if (gameOver) return;

    const row = parseInt(event.target.dataset.row);
    const col = parseInt(event.target.dataset.col);

    if (computerBoard[row][col].hit) return; // Já foi atingida

    computerBoard[row][col].hit = true;

    if (computerBoard[row][col].ship) {
        // Acerto
        const ship = computerShips.find(s => s.cells.some(c => c.row === row && c.col === col));
        ship.hits++;
        if (ship.hits === ship.size) {
            document.getElementById('status-message').textContent = `Acerto! Navio ${ship.name} afundado!`;
        } else {
            document.getElementById('status-message').textContent = 'Acerto!';
        }
    } else {
        document.getElementById('status-message').textContent = 'Erro!';
    }

    renderBoards();

    // Verificar vitória
    if (computerShips.every(ship => ship.hits === ship.size)) {
        gameOver = true;
        document.getElementById('status-message').textContent = 'Parabéns! Você venceu!';
        document.getElementById('restart-button').style.display = 'block';
        return;
    }

    // Computador ataca
    computerAttack();
}

// Ataque do computador
function computerAttack() {
    if (gameOver) return;

    let row, col;
    do {
        row = Math.floor(Math.random() * 10);
        col = Math.floor(Math.random() * 10);
    } while (playerBoard[row][col].hit);

    playerBoard[row][col].hit = true;

    if (playerBoard[row][col].ship) {
        // Acerto do computador
        const ship = playerShips.find(s => s.cells.some(c => c.row === row && c.col === col));
        ship.hits++;
        if (ship.hits === ship.size) {
            document.getElementById('status-message').textContent = `O computador acertou! Seu ${ship.name} foi afundado!`;
        } else {
            document.getElementById('status-message').textContent = 'O computador acertou!';
        }
    } else {
        document.getElementById('status-message').textContent = 'O computador errou!';
    }

    renderBoards();

    // Verificar derrota
    if (playerShips.every(ship => ship.hits === ship.size)) {
        gameOver = true;
        document.getElementById('status-message').textContent = 'Você perdeu! O computador venceu.';
        document.getElementById('restart-button').style.display = 'block';
    }
}

// Reiniciar jogo
document.getElementById('restart-button').addEventListener('click', initGame);

// Inicializar jogo ao carregar
window.addEventListener('load', initGame);