document.addEventListener('DOMContentLoaded', () => {
  const BOARD_SIZE = 10;
  const SHIPS = [
    { name: 'Porta-aviões', size: 5 },
    { name: 'Encouraçado', size: 4 },
    { name: 'Cruzador', size: 3 },
    { name: 'Submarino', size: 3 },
    { name: 'Destróier', size: 2 },
  ];

  const playerBoardEl = document.getElementById('playerBoard');
  const computerBoardEl = document.getElementById('computerBoard');
  const statusMessageEl = document.getElementById('statusMessage');
  const restartButton = document.getElementById('restartButton');

  let playerState;
  let computerState;
  let gameOver = false;

  function createBoardState() {
    return Array.from({ length: BOARD_SIZE }, () =>
      Array.from({ length: BOARD_SIZE }, () => ({
        ship: null,
        shot: false,
      }))
    );
  }

  function cloneShipsTemplate() {
    return SHIPS.map(ship => ({ ...ship, hits: 0, sunk: false }));
  }

  function randomInt(max) {
    return Math.floor(Math.random() * max);
  }

  function placeShips(state) {
    const ships = cloneShipsTemplate();

    for (const ship of ships) {
      let placed = false;
      while (!placed) {
        const horizontal = Math.random() < 0.5;
        const row = randomInt(BOARD_SIZE);
        const col = randomInt(BOARD_SIZE);
        const endRow = horizontal ? row : row + ship.size - 1;
        const endCol = horizontal ? col + ship.size - 1 : col;

        if (endRow >= BOARD_SIZE || endCol >= BOARD_SIZE) continue;

        const cells = [];
        let conflict = false;
        for (let i = 0; i < ship.size; i++) {
          const r = horizontal ? row : row + i;
          const c = horizontal ? col + i : col;
          if (state[r][c].ship) {
            conflict = true;
            break;
          }
          cells.push([r, c]);
        }

        if (conflict) continue;

        cells.forEach(([r, c]) => {
          state[r][c].ship = ship.name;
        });
        placed = true;
      }
    }

    return ships;
  }

  function createHeaderCell(text) {
    const cell = document.createElement('div');
    cell.className = 'cell cell--header';
    cell.textContent = text;
    return cell;
  }

  function renderBoard(boardEl, state, isComputerBoard) {
    boardEl.innerHTML = '';
    boardEl.appendChild(createHeaderCell(''));
    for (let c = 0; c < BOARD_SIZE; c++) {
      boardEl.appendChild(createHeaderCell(String(c + 1)));
    }

    for (let r = 0; r < BOARD_SIZE; r++) {
      boardEl.appendChild(createHeaderCell(String.fromCharCode(65 + r)));
      for (let c = 0; c < BOARD_SIZE; c++) {
        const cellData = state[r][c];
        const cell = document.createElement('div');
        cell.className = 'cell';
        cell.dataset.row = String(r);
        cell.dataset.col = String(c);
        cell.setAttribute('tabindex', '0');
        cell.setAttribute('role', 'button');
        cell.setAttribute('aria-label', `${String.fromCharCode(65 + r)}${c + 1}`);

        if (isComputerBoard) {
          cell.dataset.target = 'computer';
          if (cellData.shot) {
            cell.textContent = cellData.ship ? 'X' : 'O';
            cell.classList.add(cellData.ship ? 'cell--hit' : 'cell--miss');
          }
        } else {
          if (cellData.ship) cell.classList.add('cell--ship');
          if (cellData.shot) {
            cell.textContent = cellData.ship ? 'X' : 'O';
            cell.classList.add(cellData.ship ? 'cell--hit' : 'cell--miss');
          }
        }

        if (gameOver || (isComputerBoard && cellData.shot)) {
          cell.setAttribute('aria-disabled', 'true');
        }

        boardEl.appendChild(cell);
      }
    }
  }

  function updateStatus(message) {
    statusMessageEl.textContent = message;
  }

  function getShipByName(ships, name) {
    return ships.find(ship => ship.name === name);
  }

  function handleShot(state, ships, row, col) {
    const cell = state[row][col];
    if (cell.shot) return null;

    cell.shot = true;
    if (cell.ship) {
      const ship = getShipByName(ships, cell.ship);
      ship.hits += 1;
      if (ship.hits === ship.size) {
        ship.sunk = true;
        return { hit: true, sunk: ship.name };
      }
      return { hit: true, sunk: null };
    }

    return { hit: false, sunk: null };
  }

  function checkGameEnd(ships) {
    return ships.every(ship => ship.sunk);
  }

  function availableComputerTargets() {
    const targets = [];
    for (let r = 0; r < BOARD_SIZE; r++) {
      for (let c = 0; c < BOARD_SIZE; c++) {
        if (!playerState[r][c].shot) targets.push([r, c]);
      }
    }
    return targets;
  }

  function computerTurn() {
    const targets = availableComputerTargets();
    if (!targets.length) return;
    const [row, col] = targets[randomInt(targets.length)];
    const result = handleShot(playerState, playerShips, row, col);

    if (result.hit && result.sunk) {
      updateStatus(`Computador acertou e afundou seu ${result.sunk}.`);
    } else if (result.hit) {
      updateStatus('Computador acertou um navio seu.');
    } else {
      updateStatus('Computador errou o tiro.');
    }

    if (checkGameEnd(playerShips)) {
      gameOver = true;
      updateStatus('Derrota! Todos os seus navios foram afundados. Reinicie para jogar novamente.');
    }
  }

  function playerTurn(row, col) {
    if (gameOver) return;
    const result = handleShot(computerState, computerShips, row, col);
    if (!result) return;

    if (result.hit && result.sunk) {
      updateStatus(`Acerto! Você afundou o ${result.sunk}.`);
    } else if (result.hit) {
      updateStatus('Acerto! Você atingiu um navio.');
    } else {
      updateStatus('Erro! Você acertou a água.');
    }

    if (checkGameEnd(computerShips)) {
      gameOver = true;
      updateStatus('Vitória! Você afundou toda a frota inimiga. Reinicie para jogar novamente.');
      renderAll();
      return;
    }

    renderAll();
    computerTurn();
    renderAll();
  }

  function onBoardClick(event) {
    const target = event.target.closest('.cell');
    if (!target || target.dataset.target !== 'computer') return;
    const row = Number(target.dataset.row);
    const col = Number(target.dataset.col);
    playerTurn(row, col);
  }

  function onBoardKeydown(event) {
    const target = event.target.closest('.cell');
    if (!target || target.dataset.target !== 'computer') return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      playerTurn(Number(target.dataset.row), Number(target.dataset.col));
    }
  }

  function renderAll() {
    renderBoard(playerBoardEl, playerState, false);
    renderBoard(computerBoardEl, computerState, true);
  }

  function resetGame() {
    playerState = createBoardState();
    computerState = createBoardState();
    playerShips = placeShips(playerState);
    computerShips = placeShips(computerState);
    gameOver = false;
    updateStatus('Sua vez: escolha uma célula no tabuleiro do computador.');
    renderAll();
  }

  let playerShips = [];
  let computerShips = [];

  playerBoardEl.addEventListener('click', onBoardClick);
  computerBoardEl.addEventListener('click', onBoardClick);
  computerBoardEl.addEventListener('keydown', onBoardKeydown);
  restartButton.addEventListener('click', resetGame);

  resetGame();
});