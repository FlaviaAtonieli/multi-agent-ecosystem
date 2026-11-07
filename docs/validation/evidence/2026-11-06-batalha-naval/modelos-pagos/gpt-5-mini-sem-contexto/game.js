/*
  game.js — lógica do jogo Batalha Naval

  - Carrega quando index.html é aberto
  - Usa apenas JavaScript puro e manipulação do DOM
  - IDs principais:
      player-board  -> tabuleiro do jogador
      computer-board -> tabuleiro do computador
      status -> elemento para mensagens de status
      restart-button -> botão que reinicia o jogo

  Arquitetura resumida:
  - Representação dos tabuleiros: matriz 10x10 com objetos {shipId: number|null, hit: boolean}
  - Navios: lista de objetos {id, name, size, positions: [{r,c}], hits}
  - Posicionamento: aleatório, orientações horizontal/vertical, sem sobreposição
  - Fluxo de jogo: jogador atira clicando em célula do board do computador -> processa acerto/erro/afundado -> verifica vitória -> computador atira aleatoriamente em célula não atingida -> repete
*/

(() => {
  // Constantes
  const BOARD_SIZE = 10;
  const SHIP_TYPES = [
    { name: 'Porta-aviões', size: 5 },
    { name: 'Encouraçado', size: 4 },
    { name: 'Cruzador', size: 3 },
    { name: 'Submarino', size: 3 },
    { name: 'Destróier', size: 2 }
  ];

  // Elementos DOM estáveis
  const playerBoardEl = document.getElementById('player-board');
  const computerBoardEl = document.getElementById('computer-board');
  const statusEl = document.getElementById('status');
  const restartButton = document.getElementById('restart-button');

  // Estado do jogo
  let playerGrid, computerGrid; // 2D arrays of cells { shipId: number|null, hit: boolean }
  let playerShips, computerShips; // arrays of ship objects { id, name, size, positions: [{r,c}], hits }
  let playerTurn = true;
  let gameOver = false;
  let cpuAvailableShots = []; // array of coords available for CPU to shoot

  // Inicia ou reinicia o jogo
  function initGame() {
    // Reset state
    playerGrid = createEmptyGrid();
    computerGrid = createEmptyGrid();
    playerShips = [];
    computerShips = [];
    playerTurn = true;
    gameOver = false;

    // Place ships randomly on both boards
    placeFleetRandom(playerGrid, playerShips);
    placeFleetRandom(computerGrid, computerShips);

    // Build available shots list for CPU
    cpuAvailableShots = [];
    for (let r = 0; r < BOARD_SIZE; r++) {
      for (let c = 0; c < BOARD_SIZE; c++) {
        cpuAvailableShots.push({ r, c });
      }
    }

    // Render boards
    renderBoard(playerBoardEl, playerGrid, true);
    renderBoard(computerBoardEl, computerGrid, false);

    setStatus('Sua vez. Clique no tabuleiro do computador para atirar.');

    // Attach handlers
    attachComputerBoardHandlers();
  }

  // Cria uma grade vazia 10x10
  function createEmptyGrid() {
    const g = new Array(BOARD_SIZE);
    for (let r = 0; r < BOARD_SIZE; r++) {
      g[r] = new Array(BOARD_SIZE);
      for (let c = 0; c < BOARD_SIZE; c++) {
        g[r][c] = { shipId: null, hit: false };
      }
    }
    return g;
  }

  // Posiciona a frota aleatoriamente em um grid e popula a lista de navios
  function placeFleetRandom(grid, shipsList) {
    let shipIdCounter = 1;
    for (const type of SHIP_TYPES) {
      const ship = { id: shipIdCounter++, name: type.name, size: type.size, positions: [], hits: 0 };
      let placed = false;
      // Tentativas até posicionar (este laço garante eventual posicionamento em tabuleiro 10x10)
      while (!placed) {
        const horizontal = Math.random() < 0.5;
        const maxR = horizontal ? BOARD_SIZE : BOARD_SIZE - type.size + 1;
        const maxC = horizontal ? BOARD_SIZE - type.size + 1 : BOARD_SIZE;
        const startR = Math.floor(Math.random() * maxR);
        const startC = Math.floor(Math.random() * maxC);

        // Verifica se cabe e não colide
        let collision = false;
        const candidate = [];
        for (let i = 0; i < type.size; i++) {
          const r = startR + (horizontal ? 0 : i);
          const c = startC + (horizontal ? i : 0);
          if (grid[r][c].shipId !== null) { collision = true; break; }
          candidate.push({ r, c });
        }

        if (!collision) {
          // Coloca
          for (const pos of candidate) {
            grid[pos.r][pos.c].shipId = ship.id;
            ship.positions.push({ r: pos.r, c: pos.c });
          }
          shipsList.push(ship);
          placed = true;
        }
      }
    }
  }

  // Renderiza um tabuleiro no elemento fornecido. Se isPlayer=true, mostra navios.
  function renderBoard(boardEl, grid, isPlayer) {
    // Limpa
    boardEl.innerHTML = '';
    boardEl.classList.toggle('player', !!isPlayer);
    boardEl.classList.toggle('computer', !isPlayer);

    for (let r = 0; r < BOARD_SIZE; r++) {
      for (let c = 0; c < BOARD_SIZE; c++) {
        const cell = document.createElement('div');
        cell.className = 'cell';
        cell.dataset.row = r;
        cell.dataset.col = c;
        cell.setAttribute('role', 'button');
        cell.setAttribute('aria-label', `Linha ${r + 1} Coluna ${c + 1}`);

        const cellData = grid[r][c];

        // Exibir estado
        if (cellData.hit) {
          if (cellData.shipId !== null) {
            cell.classList.add('hit');
          } else {
            cell.classList.add('miss');
          }
        } else {
          // Não atingido ainda. Para jogador, exibir navios visuais.
          if (isPlayer && cellData.shipId !== null) {
            cell.classList.add('ship');
          }
        }

        // If ship is sunk, mark its positions as 'sunk'
        if (cellData.shipId !== null) {
          const shipList = isPlayer ? playerShips : computerShips;
          const ship = shipList.find(s => s.id === cellData.shipId);
          if (ship && ship.hits >= ship.size) {
            cell.classList.remove('hit');
            cell.classList.remove('ship');
            cell.classList.add('sunk');
          }
        }

        boardEl.appendChild(cell);
      }
    }
  }

  // Anexa manipuladores ao tabuleiro do computador para permitir cliques do jogador
  function attachComputerBoardHandlers() {
    // Remove handler previos (se houver)
    computerBoardEl.replaceWith(computerBoardEl.cloneNode(false));
    // Re-query element
    const newComputerBoardEl = document.getElementById('computer-board');

    newComputerBoardEl.addEventListener('click', (ev) => {
      if (gameOver) return;
      if (!playerTurn) return; // evita clique enquanto CPU pensa

      const target = ev.target;
      if (!target.classList.contains('cell')) return;
      const r = Number(target.dataset.row);
      const c = Number(target.dataset.col);

      // Cell already shot?
      if (computerGrid[r][c].hit) return;

      playerTurn = false;
      processPlayerShot(r, c);
    });

    // Ensure we reflect UI
    renderBoard(newComputerBoardEl, computerGrid, false);
  }

  // Processa o tiro do jogador no tabuleiro do computador
  function processPlayerShot(r, c) {
    const cell = computerGrid[r][c];
    cell.hit = true;

    if (cell.shipId !== null) {
      // Hit
      const ship = computerShips.find(s => s.id === cell.shipId);
      ship.hits++;
      renderBoard(computerBoardEl, computerGrid, false);
      if (ship.hits >= ship.size) {
        setStatus(`Você afundou o ${ship.name}!`);
      } else {
        setStatus('Acertou!');
      }

      // Verifica vitória
      if (checkAllSunk(computerShips)) {
        renderBoard(computerBoardEl, computerGrid, false);
        endGame(true);
        return;
      }

      // CPU responde após pequeno atraso
      setTimeout(() => cpuTurn(), 500);

    } else {
      // Miss
      renderBoard(computerBoardEl, computerGrid, false);
      setStatus('Água (erro).');
      // CPU responde após pequeno atraso
      setTimeout(() => cpuTurn(), 500);
    }
  }

  // Turno do computador — escolhe aleatoriamente uma célula ainda não atingida no tabuleiro do jogador
  function cpuTurn() {
    if (gameOver) return;

    // Remove already-shot cells from available list lazily
    cpuAvailableShots = cpuAvailableShots.filter(coord => !playerGrid[coord.r][coord.c].hit);
    if (cpuAvailableShots.length === 0) {
      // Sem células restantes — empate (teoricamente não ocorre)
      endGame(false, 'Empate.');
      return;
    }

    // Escolhe aleatoriamente
    const idx = Math.floor(Math.random() * cpuAvailableShots.length);
    const shot = cpuAvailableShots.splice(idx, 1)[0];

    const r = shot.r;
    const c = shot.c;
    const cell = playerGrid[r][c];
    cell.hit = true;

    if (cell.shipId !== null) {
      const ship = playerShips.find(s => s.id === cell.shipId);
      ship.hits++;
      renderBoard(playerBoardEl, playerGrid, true);
      if (ship.hits >= ship.size) {
        setStatus(`Computador afundou seu ${ship.name}!`);
      } else {
        setStatus('Computador acertou seu navio!');
      }

      if (checkAllSunk(playerShips)) {
        endGame(false);
        return;
      }

      // Depois de um acerto do CPU, volta para o jogador
      playerTurn = true;
    } else {
      renderBoard(playerBoardEl, playerGrid, true);
      setStatus('Computador errou. Sua vez.');
      playerTurn = true;
    }
  }

  // Verifica se todas embarcações da lista estão afundadas
  function checkAllSunk(ships) {
    return ships.every(s => s.hits >= s.size);
  }

  // Define mensagem de status
  function setStatus(text) {
    statusEl.textContent = text;
  }

  // Finaliza jogo e mostra resultado. playerWon=true se jogador venceu
  function endGame(playerWon, customMessage) {
    gameOver = true;
    if (customMessage) {
      setStatus(customMessage);
    } else if (playerWon) {
      setStatus('Parabéns! Você venceu!');
    } else {
      setStatus('Você foi derrotado.');
    }
    // Revela posições do computador (mostra navios afundados e não afundados como sunk/ship/hit)
    renderBoard(playerBoardEl, playerGrid, true);
    renderBoard(computerBoardEl, computerGrid, false);
  }

  // Monta navios no tabuleiro do jogador para fins de visibilidade (já feito no placeFleetRandom)
  // Anexa evento do botão reiniciar
  restartButton.addEventListener('click', () => {
    initGame();
  });

  // Inicialização do jogo — monta tabuleiros e posiciona navios
  // Precisamos também construir os elementos iniciais dos tabuleiros quando a página carrega
  function buildEmptyBoardElements() {
    // Player
    playerBoardEl.innerHTML = '';
    playerBoardEl.classList.add('player');

    // Computer
    computerBoardEl.innerHTML = '';
    computerBoardEl.classList.add('computer');
  }

  // Start
  buildEmptyBoardElements();
  initGame();

  // Expor nenhum método global (IIFE)
})();
