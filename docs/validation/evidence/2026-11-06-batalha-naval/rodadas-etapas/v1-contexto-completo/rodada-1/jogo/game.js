// Batalha Naval - Jogo Completo
// Desenvolvido em JavaScript puro

class BattleshipGame {
    constructor() {
        this.playerBoard = Array(10).fill().map(() => Array(10).fill(null));
        this.computerBoard = Array(10).fill().map(() => Array(10).fill(null));
        this.playerShots = Array(10).fill().map(() => Array(10).fill(false));
        this.computerShots = Array(10).fill().map(() => Array(10).fill(false));
        this.gameOver = false;
        this.playerTurn = true;
        
        this.ships = [
            { name: 'Porta-aviões', size: 5 },
            { name: 'Encouraçado', size: 4 },
            { name: 'Cruzador', size: 3 },
            { name: 'Submarino', size: 3 },
            { name: 'Destróier', size: 2 }
        ];
        
        this.init();
    }
    
    init() {
        this.createBoards();
        this.placeShips(this.computerBoard);
        this.setupEventListeners();
        this.updateMessage('Clique no tabuleiro do computador para começar!');
    }
    
    createBoards() {
        const playerBoard = document.getElementById('player-board');
        const computerBoard = document.getElementById('computer-board');
        
        // Limpar tabuleiros
        playerBoard.innerHTML = '';
        computerBoard.innerHTML = '';
        
        // Criar tabuleiro do jogador
        for (let row = 0; row < 10; row++) {
            for (let col = 0; col < 10; col++) {
                const cell = document.createElement('div');
                cell.className = 'cell';
                cell.dataset.row = row;
                cell.dataset.col = col;
                cell.dataset.type = 'player';
                playerBoard.appendChild(cell);
            }
        }
        
        // Criar tabuleiro do computador
        for (let row = 0; row < 10; row++) {
            for (let col = 0; col < 10; col++) {
                const cell = document.createElement('div');
                cell.className = 'cell';
                cell.dataset.row = row;
                cell.dataset.col = col;
                cell.dataset.type = 'computer';
                computerBoard.appendChild(cell);
            }
        }
    }
    
    placeShips(board) {
        // Limpar o tabuleiro
        for (let row = 0; row < 10; row++) {
            for (let col = 0; col < 10; col++) {
                board[row][col] = null;
            }
        }
        
        // Posicionar cada navio
        this.ships.forEach(ship => {
            let placed = false;
            while (!placed) {
                const horizontal = Math.random() < 0.5;
                const row = Math.floor(Math.random() * 10);
                const col = Math.floor(Math.random() * 10);
                
                if (this.canPlaceShip(board, row, col, ship.size, horizontal)) {
                    this.placeShipAt(board, row, col, ship.size, horizontal, ship.name);
                    placed = true;
                }
            }
        });
    }
    
    canPlaceShip(board, row, col, size, horizontal) {
        for (let i = 0; i < size; i++) {
            const currentRow = horizontal ? row : row + i;
            const currentCol = horizontal ? col + i : col;
            
            if (currentRow >= 10 || currentCol >= 10 || board[currentRow][currentCol] !== null) {
                return false;
            }
        }
        return true;
    }
    
    placeShipAt(board, row, col, size, horizontal, shipName) {
        for (let i = 0; i < size; i++) {
            const currentRow = horizontal ? row : row + i;
            const currentCol = horizontal ? col + i : col;
            board[currentRow][currentCol] = shipName;
        }
    }
    
    setupEventListeners() {
        const computerBoard = document.getElementById('computer-board');
        const restartBtn = document.getElementById('restart-btn');
        
        computerBoard.addEventListener('click', (e) => this.handlePlayerAttack(e));
        restartBtn.addEventListener('click', () => this.restartGame());
    }
    
    handlePlayerAttack(event) {
        if (this.gameOver || !this.playerTurn) return;
        
        const cell = event.target;
        const row = parseInt(cell.dataset.row);
        const col = parseInt(cell.dataset.col);
        
        if (this.playerShots[row][col]) {
            this.updateMessage('Casa já atingida! Tente novamente.');
            return;
        }
        
        this.playerShots[row][col] = true;
        
        if (this.computerBoard[row][col] !== null) {
            cell.classList.add('hit');
            cell.textContent = 'X';
            this.updateMessage('Acerto!');
            
            // Verificar se o navio foi afundado
            if (this.isShipSunk(this.computerBoard, this.playerShots, this.computerBoard[row][col])) {
                this.updateMessage(`Acerto! Navio ${this.computerBoard[row][col]} afundado!`);
            }
            
            // Verificar vitória
            if (this.checkWin(this.computerBoard, this.playerShots)) {
                this.endGame('Parabéns! Você venceu!');
                return;
            }
        } else {
            cell.classList.add('miss');
            cell.textContent = 'O';
            this.updateMessage('Errou!');
        }
        
        this.playerTurn = false;
        setTimeout(() => this.computerAttack(), 1000);
    }
    
    computerAttack() {
        if (this.gameOver) return;
        
        let row, col;
        do {
            row = Math.floor(Math.random() * 10);
            col = Math.floor(Math.random() * 10);
        } while (this.computerShots[row][col]);
        
        this.computerShots[row][col] = true;
        
        const cell = document.querySelector(`#player-board .cell[data-row="${row}"][data-col="${col}"]`);
        
        if (this.playerBoard[row][col] !== null) {
            cell.classList.add('hit');
            cell.textContent = 'X';
            this.updateMessage('Computador acertou seu navio!');
            
            // Verificar se o navio foi afundado
            if (this.isShipSunk(this.playerBoard, this.computerShots, this.playerBoard[row][col])) {
                this.updateMessage(`Computador afundou seu ${this.playerBoard[row][col]}!`);
            }
            
            // Verificar derrota
            if (this.checkWin(this.playerBoard, this.computerShots)) {
                this.endGame('Computador venceu! Você perdeu.');
                return;
            }
        } else {
            cell.classList.add('miss');
            cell.textContent = 'O';
            this.updateMessage('Computador errou!');
        }
        
        this.playerTurn = true;
    }
    
    isShipSunk(board, shots, shipName) {
        for (let row = 0; row < 10; row++) {
            for (let col = 0; col < 10; col++) {
                if (board[row][col] === shipName && !shots[row][col]) {
                    return false;
                }
            }
        }
        return true;
    }
    
    checkWin(board, shots) {
        for (let row = 0; row < 10; row++) {
            for (let col = 0; col < 10; col++) {
                if (board[row][col] !== null && !shots[row][col]) {
                    return false;
                }
            }
        }
        return true;
    }
    
    endGame(message) {
        this.gameOver = true;
        this.updateMessage(`${message} Jogo terminado!`);
        document.getElementById('restart-btn').disabled = false;
    }
    
    updateMessage(message) {
        document.getElementById('message').textContent = message;
    }
    
    restartGame() {
        // Reinicializar estado do jogo
        this.playerBoard = Array(10).fill().map(() => Array(10).fill(null));
        this.computerBoard = Array(10).fill().map(() => Array(10).fill(null));
        this.playerShots = Array(10).fill().map(() => Array(10).fill(false));
        this.computerShots = Array(10).fill().map(() => Array(10).fill(false));
        this.gameOver = false;
        this.playerTurn = true;
        
        // Recriar tabuleiros e posicionamento
        this.createBoards();
        this.placeShips(this.computerBoard);
        this.setupEventListeners();
        this.updateMessage('Clique no tabuleiro do computador para começar!');
        document.getElementById('restart-btn').disabled = true;
    }
}

// Inicializar o jogo quando a página carregar
document.addEventListener('DOMContentLoaded', () => {
    new BattleshipGame();
});