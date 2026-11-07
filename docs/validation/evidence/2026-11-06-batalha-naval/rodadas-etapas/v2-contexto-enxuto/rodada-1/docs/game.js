// game.js - Lógica do jogo Batalha Naval

class BattleshipGame {
    constructor() {
        this.playerBoard = this.createBoard();
        this.computerBoard = this.createBoard();
        this.playerShips = [];
        this.computerShips = [];
        this.gameOver = false;
        this.currentPlayer = 'player';
        this.init();
    }

    createBoard() {
        return Array(10).fill().map(() => Array(10).fill(null));
    }

    init() {
        this.setupEventListeners();
        this.placeShips(this.playerBoard, this.playerShips, true);
        this.placeShips(this.computerBoard, this.computerShips, false);
        this.renderBoards();
    }

    setupEventListeners() {
        document.getElementById('restart-btn').addEventListener('click', () => this.restartGame());
    }

    placeShips(board, ships, isPlayer) {
        const shipTypes = [
            { name: 'porta-aviões', size: 5 },
            { name: 'encouraçado', size: 4 },
            { name: 'cruzador', size: 3 },
            { name: 'submarino', size: 3 },
            { name: 'destróier', size: 2 }
        ];

        for (const shipType of shipTypes) {
            let placed = false;
            while (!placed) {
                const orientation = Math.random() < 0.5 ? 'horizontal' : 'vertical';
                const row = Math.floor(Math.random() * 10);
                const col = Math.floor(Math.random() * 10);
                
                if (this.canPlaceShip(board, row, col, shipType.size, orientation)) {
                    const ship = {
                        name: shipType.name,
                        size: shipType.size,
                        positions: [],
                        hits: 0
                    };
                    
                    for (let i = 0; i < shipType.size; i++) {
                        const r = orientation === 'horizontal' ? row : row + i;
                        const c = orientation === 'vertical' ? col + i : col;
                        board[r][c] = ship;
                        ship.positions.push([r, c]);
                    }
                    
                    ships.push(ship);
                    placed = true;
                }
            }
        }
    }

    canPlaceShip(board, row, col, size, orientation) {
        for (let i = 0; i < size; i++) {
            const r = orientation === 'horizontal' ? row : row + i;
            const c = orientation === 'vertical' ? col + i : col;
            
            if (r < 0 || r >= 10 || c < 0 || c >= 10) return false;
            if (board[r][c] !== null) return false;
        }
        return true;
    }

    renderBoards() {
        this.renderBoard('player-board', this.playerBoard, false);
        this.renderBoard('computer-board', this.computerBoard, true);
    }

    renderBoard(boardId, board, isComputer) {
        const boardElement = document.getElementById(boardId);
        boardElement.innerHTML = '';
        
        for (let row = 0; row < 10; row++) {
            for (let col = 0; col < 10; col++) {
                const cell = document.createElement('div');
                cell.className = 'cell';
                cell.dataset.row = row;
                cell.dataset.col = col;
                
                if (!isComputer && board[row][col]) {
                    cell.classList.add('ship');
                }
                
                if (isComputer) {
                    cell.addEventListener('click', () => this.handlePlayerAttack(row, col));
                }
                
                boardElement.appendChild(cell);
            }
        }
    }

    handlePlayerAttack(row, col) {
        if (this.gameOver || this.currentPlayer !== 'player') return;
        
        const cell = this.computerBoard[row][col];
        const cellElement = document.querySelector(`#computer-board .cell[data-row="${row}"][data-col="${col}"]`);
        
        if (cellElement.classList.contains('hit') || cellElement.classList.contains('miss')) {
            this.updateStatus('Você já atirou em essa casa! Tente outro lugar.');
            return;
        }
        
        if (cell) {
            cellElement.classList.add('hit');
            cell.hits++;
            
            if (cell.hits === cell.size) {
                cell.positions.forEach(([r, c]) => {
                    document.querySelector(`#computer-board .cell[data-row="${r}"][data-col="${c}"]`).classList.add('sunk');
                });
                this.updateStatus(`Acerto! Navio ${cell.name} afundado!`);
            } else {
                this.updateStatus('Acerto!');
            }
            
            if (this.checkWin(this.computerShips)) {
                this.endGame('player');
                return;
            }
        } else {
            cellElement.classList.add('miss');
            this.updateStatus('Água!');
        }
        
        this.currentPlayer = 'computer';
        setTimeout(() => this.computerAttack(), 500);
    }

    computerAttack() {
        if (this.gameOver) return;
        
        let row, col;
        do {
            row = Math.floor(Math.random() * 10);
            col = Math.floor(Math.random() * 10);
        } while (this.wasAttacked(row, col));
        
        const cell = this.playerBoard[row][col];
        const cellElement = document.querySelector(`#player-board .cell[data-row="${row}"][data-col="${col}"]`);
        
        if (cell) {
            cellElement.classList.add('hit');
            cell.hits++;
            
            if (cell.hits === cell.size) {
                cell.positions.forEach(([r, c]) => {
                    document.querySelector(`#player-board .cell[data-row="${r}"][data-col="${c}"]`).classList.add('sunk');
                });
                this.updateStatus(`Computador acertou! Seu navio ${cell.name} foi afundado!`);
            } else {
                this.updateStatus('Computador acertou!');
            }
            
            if (this.checkWin(this.playerShips)) {
                this.endGame('computer');
                return;
            }
        } else {
            cellElement.classList.add('miss');
            this.updateStatus('Computador errou!');
        }
        
        this.currentPlayer = 'player';
    }

    wasAttacked(row, col) {
        const cellElement = document.querySelector(`#player-board .cell[data-row="${row}"][data-col="${col}"]`);
        return cellElement.classList.contains('hit') || cellElement.classList.contains('miss');
    }

    checkWin(ships) {
        return ships.every(ship => ship.hits === ship.size);
    }

    endGame(winner) {
        this.gameOver = true;
        if (winner === 'player') {
            document.getElementById('status').innerHTML = '<span class="victory">Vitória! Você destruiu a frota inimiga!</span>';
        } else {
            document.getElementById('status').innerHTML = '<span class="defeat">Derrota! Sua frota foi destruída.</span>';
        }
    }

    updateStatus(message) {
        document.getElementById('status').textContent = message;
    }

    restartGame() {
        this.playerBoard = this.createBoard();
        this.computerBoard = this.createBoard();
        this.playerShips = [];
        this.computerShips = [];
        this.gameOver = false;
        this.currentPlayer = 'player';
        
        this.placeShips(this.playerBoard, this.playerShips, true);
        this.placeShips(this.computerBoard, this.computerShips, false);
        this.renderBoards();
        this.updateStatus('Clique nas casas do tabuleiro do computador para atirar!');
    }
}

// Inicializar o jogo quando a página carrega
document.addEventListener('DOMContentLoaded', () => {
    new BattleshipGame();
});