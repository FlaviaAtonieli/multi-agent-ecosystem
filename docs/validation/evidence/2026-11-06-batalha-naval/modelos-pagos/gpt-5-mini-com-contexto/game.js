// game.js - Lógica completa do jogo de Batalha Naval

// Constantes do tabuleiro
const COLS = 10;
const ROWS = 10;
const COL_LABELS = ['A','B','C','D','E','F','G','H','I','J'];
const ROW_LABELS = ['1','2','3','4','5','6','7','8','9','10'];

// Elementos estáveis
const playerBoardEl = document.getElementById('player-board');
const computerBoardEl = document.getElementById('computer-board');
const statusEl = document.getElementById('status');
const restartBtn = document.getElementById('restart-btn');

// Definição da frota
const SHIP_TYPES = [
  { id: 'carrier', name: 'Porta-aviões', size: 5 },
  { id: 'battleship', name: 'Encouraçado', size: 4 },
  { id: 'cruiser', name: 'Cruzador', size: 3 },
  { id: 'submarine', name: 'Submarino', size: 3 },
  { id: 'destroyer', name: 'Destróier', size: 2 }
];

// Estado do jogo
let playerBoard;       // matriz ROWS x COLS com null ou shipId
let computerBoard;     // mesma estrutura
let playerShips;       // array de objetos ship {id,name,size,positions:[{r,c}],hits}
let computerShips;
let gameOver = false;

// Para atalhos de teclado
let pendingCol = null; // 0..9
let pendingRow = null; // 0..9

// Inicialização
function init() {
  playerBoard = createEmptyBoard();
  computerBoard = createEmptyBoard();
  playerShips = [];
  computerShips = [];
  gameOver = false;
  pendingCol = null; pendingRow = null;

  clearElement(playerBoardEl);
  clearElement(computerBoardEl);

  createBoardDOM(playerBoardEl, false);
  createBoardDOM(computerBoardEl, true);

  placeFleetRandom(playerBoard, playerShips);
  placeFleetRandom(computerBoard, computerShips);

  renderPlayerShips();
  statusEl.textContent = 'Sua vez — atire no tabuleiro do computador.';
}

function createEmptyBoard(){
  const b = new Array(ROWS);
  for(let r=0;r<ROWS;r++){
    b[r] = new Array(COLS).fill(null);
  }
  return b;
}

function clearElement(el){
  while(el.firstChild) el.removeChild(el.firstChild);
}

function createBoardDOM(container, isComputer){
  for(let r=0;r<ROWS;r++){
    for(let c=0;c<COLS;c++){
      const cell = document.createElement('div');
      cell.className = 'cell';
      const coord = COL_LABELS[c] + ROW_LABELS[r];
      cell.dataset.coord = coord;
      cell.dataset.row = String(r);
      cell.dataset.col = String(c);
      cell.setAttribute('tabindex','0');
      cell.setAttribute('role','button');
      cell.setAttribute('aria-label', `${isComputer ? 'Computador' : 'Jogador'}: ${coord}`);

      // exibe coordenada pequena para testes manuais
      const coordEl = document.createElement('span');
      coordEl.className = 'coord';
      coordEl.textContent = coord;
      cell.appendChild(coordEl);

      if(isComputer){
        // Só o tabuleiro do computador recebe cliques/ataques do jogador
        cell.addEventListener('click', onPlayerFire);
        cell.addEventListener('keydown', (ev) => {
          if(ev.key === 'Enter' || ev.key === ' '){ ev.preventDefault(); cell.click(); }
        });
      } else {
        // permitir foco e ativação por teclado para inspeção
        cell.addEventListener('keydown', (ev) => {
          if(ev.key === 'Enter' || ev.key === ' '){ ev.preventDefault(); }
        });
      }

      container.appendChild(cell);
    }
  }
}

function placeFleetRandom(board, shipsArray){
  for(const type of SHIP_TYPES){
    let placed = false;
    let attempts = 0;
    while(!placed && attempts < 1000){
      attempts++;
      const horizontal = Math.random() < 0.5;
      const maxRow = horizontal ? ROWS - 1 : ROWS - type.size;
      const maxCol = horizontal ? COLS - type.size : COLS - 1;
      const r0 = getRandomInt(0, maxRow);
      const c0 = getRandomInt(0, maxCol);

      // compute candidate positions
      const positions = [];
      let conflict = false;
      for(let i=0;i<type.size;i++){
        const r = horizontal ? r0 : r0 + i;
        const c = horizontal ? c0 + i : c0;
        if(board[r][c] !== null){ conflict = true; break; }
        positions.push({r,c});
      }
      if(conflict) continue;

      // place ship
      for(const pos of positions) board[pos.r][pos.c] = type.id;
      shipsArray.push({ id: type.id, name: type.name, size: type.size, positions, hits: 0, sunk: false });
      placed = true;
    }
    if(!placed){
      console.error('Falha ao posicionar navio:', type);
      // Em caso extremo, continuar sem esse navio (não deve acontecer com 1000 tentativas)
    }
  }
}

function getRandomInt(min, max){
  // inclusive min, inclusive max
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function renderPlayerShips(){
  // Mostra navios do jogador visualmente
  const cells = playerBoardEl.querySelectorAll('.cell');
  cells.forEach(el => {
    const r = Number(el.dataset.row);
    const c = Number(el.dataset.col);
    const val = playerBoard[r][c];
    if(val){
      el.classList.add('ship');
      el.title = `Navio: ${val}`;
    } else {
      el.classList.remove('ship');
      el.title = '';
    }
  });
}

// Evento de clique do jogador no tabuleiro do computador
function onPlayerFire(ev){
  if(gameOver) return;
  const cell = ev.currentTarget;
  handlePlayerShot(cell);
}

function handlePlayerShot(cell){
  const r = Number(cell.dataset.row);
  const c = Number(cell.dataset.col);
  const coord = COL_LABELS[c] + ROW_LABELS[r];

  // Verificar se já foi atingido
  if(cell.classList.contains('hit') || cell.classList.contains('miss') || cell.classList.contains('sunk')){
    statusEl.textContent = `Coordenada ${coord} já foi atacada.`;
    return;
  }

  // Revelar se acertou navio no computador
  const shipId = computerBoard[r][c];
  if(shipId){
    cell.classList.add('hit');
    const ship = computerShips.find(s => s.id === shipId);
    ship.hits++;
    statusEl.textContent = `Acerto! ${coord}`;

    if(ship.hits >= ship.size){
      ship.sunk = true;
      statusEl.textContent = `Afundou ${ship.name}! 🚢`;
      // marcar todas as posições como 'sunk' no DOM
      for(const pos of ship.positions){
        const selector = `.cell[data-row='${pos.r}'][data-col='${pos.c}']`;
        const el = computerBoardEl.querySelector(selector);
        if(el){ el.classList.remove('hit'); el.classList.add('sunk'); }
      }
    }

  } else {
    cell.classList.add('miss');
    statusEl.textContent = `Erro. ${coord}`;
  }

  // Verificar vitória do jogador
  if(allShipsSunk(computerShips)){
    statusEl.textContent = 'Parabéns — você venceu! 🎉';
    gameOver = true;
    return;
  }

  // Se jogo não terminou, computador atira
  // Peque um pequeno atraso para simular vez do adversário
  setTimeout(computerTurn, 600);
}

function allShipsSunk(ships){
  return ships.every(s => s.sunk === true);
}

function computerTurn(){
  if(gameOver) return;
  // escolher aleatoriamente uma célula do jogador que ainda não foi atacada
  const available = [];
  for(let r=0;r<ROWS;r++){
    for(let c=0;c<COLS;c++){
      const selector = `.cell[data-row='${r}'][data-col='${c}']`;
      const el = playerBoardEl.querySelector(selector);
      if(el && !el.classList.contains('hit') && !el.classList.contains('miss') && !el.classList.contains('sunk')){
        available.push({r,c,el});
      }
    }
  }
  if(available.length === 0){
    statusEl.textContent = 'Empate improvável — sem casas para atacar.';
    gameOver = true;
    return;
  }
  const choice = available[getRandomInt(0, available.length - 1)];
  const {r,c,el} = choice;
  const coord = COL_LABELS[c] + ROW_LABELS[r];

  const shipId = playerBoard[r][c];
  if(shipId){
    el.classList.add('hit');
    const ship = playerShips.find(s => s.id === shipId);
    ship.hits++;
    statusEl.textContent = `O computador acertou em ${coord}!`;

    if(ship.hits >= ship.size){
      ship.sunk = true;
      statusEl.textContent = `Seu ${ship.name} foi afundado! 💥`;
      for(const pos of ship.positions){
        const selector = `.cell[data-row='${pos.r}'][data-col='${pos.c}']`;
        const el2 = playerBoardEl.querySelector(selector);
        if(el2){ el2.classList.remove('hit'); el2.classList.add('sunk'); }
      }
    }
  } else {
    el.classList.add('miss');
    statusEl.textContent = `O computador errou em ${coord}.`;
  }

  // Verificar derrota do jogador
  if(allShipsSunk(playerShips)){
    statusEl.textContent = 'Você perdeu — o computador venceu. 😞';
    gameOver = true;
    return;
  }

  // Volta para o jogador
  statusEl.textContent = statusEl.textContent + ' Sua vez.';
}

// Tratamento de atalhos de seleção por teclado
window.addEventListener('keydown', (ev) => {
  if(gameOver) return;
  const key = ev.key.toLowerCase();

  // Colunas: a-j
  if(key >= 'a' && key <= 'j'){
    pendingCol = key.charCodeAt(0) - 'a'.charCodeAt(0);
    showPendingSelection();
    ev.preventDefault();
    return;
  }
  // Linhas: 1-9 and 0 (0 -> 10)
  if((key >= '1' && key <= '9') || key === '0'){
    if(key === '0') pendingRow = 9; else pendingRow = Number(key) - 1;
    showPendingSelection();
    ev.preventDefault();
    // Se ambos definidos, executar tiro
    if(pendingCol !== null && pendingRow !== null){
      fireAtPending();
    }
    return;
  }
  // Cancelar seleção com Escape
  if(key === 'escape'){
    pendingCol = null; pendingRow = null; clearSelectionHighlights();
    statusEl.textContent = 'Seleção cancelada.';
  }
});

function showPendingSelection(){
  clearSelectionHighlights();
  if(pendingCol === null && pendingRow === null) return;
  // se ambos definidos, destacar única célula; se só um, destacar linha/coluna
  if(pendingCol !== null && pendingRow !== null){
    const selector = `.cell[data-row='${pendingRow}'][data-col='${pendingCol}']`;
    const el = computerBoardEl.querySelector(selector);
    if(el) el.classList.add('selected');
    statusEl.textContent = `Selecionado ${COL_LABELS[pendingCol]}${ROW_LABELS[pendingRow]}. Pressione Enter para confirmar ou pressione coluna/linha para mudar.`;
  } else if(pendingCol !== null){
    statusEl.textContent = `Coluna ${COL_LABELS[pendingCol]} selecionada. Agora escolha a linha (1-10).`;
  } else if(pendingRow !== null){
    statusEl.textContent = `Linha ${ROW_LABELS[pendingRow]} selecionada. Agora escolha a coluna (A-J).`;
  }
}

function clearSelectionHighlights(){
  const prev = computerBoardEl.querySelectorAll('.cell.selected');
  prev.forEach(el => el.classList.remove('selected'));
}

function fireAtPending(){
  const selector = `.cell[data-row='${pendingRow}'][data-col='${pendingCol}']`;
  const el = computerBoardEl.querySelector(selector);
  if(el){
    // Simular click
    el.click();
  }
  pendingCol = null; pendingRow = null;
  clearSelectionHighlights();
}

// Também permitir disparar via Enter/Space quando uma célula do tabuleiro do computador estiver focada
computerBoardEl.addEventListener('keydown', (ev) => {
  if(gameOver) return;
  if(ev.key === 'Enter' || ev.key === ' '){ ev.preventDefault(); const el = document.activeElement; if(el && el.classList.contains('cell')) el.click(); }
});

// Reiniciar jogo
restartBtn.addEventListener('click', () => { init(); });

// Ao carregar a página, inicializar tudo e posicionar navios do jogador e computador
window.addEventListener('DOMContentLoaded', () => {
  init();
});

// Função auxiliar para testes/debug — expõe contagem de navios (não usada na UI)
function debugCounts(){
  console.log('playerShips', playerShips.map(s => ({id:s.id,size:s.size,hits:s.hits,sunk:s.sunk})))
  console.log('computerShips', computerShips.map(s => ({id:s.id,size:s.size,hits:s.hits,sunk:s.sunk})))
}
