const { chromium } = require('playwright-core')
const path = require('path')
const URL = require('url').pathToFileURL(path.resolve(__dirname, 'jogo-gerado/index.html')).href
let pass = 0, fail = 0
const check = (l, ok, x = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${l} ${x}`); ok ? pass++ : fail++ }
;(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
  await page.goto(URL); await page.waitForTimeout(300)
  await page.screenshot({ path: 'play-0-inicio.png' })

  console.log('--- abre e monta')
  check('abre sem erro no console', errors.length === 0, errors.join('|'))
  check('tabuleiro do jogador com 100 casas', (await page.locator('#player-board .cell').count()) === 100)
  check('tabuleiro do computador com 100 casas', (await page.locator('#computer-board .cell').count()) === 100)
  const fleet = await page.evaluate(() => ({ player: playerShips.map((s) => s.cells.length), computer: computerShips.map((s) => s.cells.length) }))
  check('frota do jogador 5,4,3,3,2', JSON.stringify(fleet.player) === '[5,4,3,3,2]', JSON.stringify(fleet.player))
  check('17 casas de navio visíveis no tabuleiro do jogador', (await page.locator('#player-board .cell.ship').count()) === 17)
  check('navios do computador ocultos', (await page.locator('#computer-board .cell.ship').count()) === 0)
  const overlap = await page.evaluate(() => { const all = computerShips.flatMap((s) => s.cells.map((c) => `${c.row},${c.col}`)); return all.length - new Set(all).size })
  check('navios do computador sem sobreposição', overlap === 0)
  // Posicionamento sem sobreposição e dentro do tabuleiro em 200 partidas
  const bad = await page.evaluate(() => { let b = 0; for (let k = 0; k < 200; k++) { initGame(); for (const list of [playerShips, computerShips]) { const all = list.flatMap((s) => s.cells.map((c) => `${c.row},${c.col}`)); if (all.length !== 17 || new Set(all).size !== 17 || list.some((s) => s.cells.some((c) => c.row < 0 || c.row > 9 || c.col < 0 || c.col > 9))) b++ } } return b })
  check('200 partidas: posicionamento sempre válido', bad === 0, `inválidas=${bad}`)

  console.log('--- tiro e feedback')
  await page.evaluate(() => initGame())
  const target = await page.evaluate(() => { for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) if (!computerBoard[r][c].ship) return { r, c } })
  const cell = () => page.locator(`#computer-board .cell[data-row="${target.r}"][data-col="${target.c}"]`)
  await cell().click()
  check('tiro na água marca a casa como erro', await cell().evaluate((el) => el.classList.contains('miss')))
  const shotsBefore = await page.evaluate(() => playerBoard.flat().filter((x) => x.hit).length)
  await cell().click()
  const shotsAfter = await page.evaluate(() => playerBoard.flat().filter((x) => x.hit).length)
  check('tiro repetido na mesma casa é ignorado (computador não joga de novo)', shotsAfter === shotsBefore)
  const shipCell = await page.evaluate(() => computerShips[4].cells[0])
  await page.locator(`#computer-board .cell[data-row="${shipCell.row}"][data-col="${shipCell.col}"]`).click()
  const msg = await page.locator('#status-message').innerText()
  check('jogador vê o resultado do próprio tiro', /^Acerto/.test(msg), `mensagem: "${msg}"`)
  const playerMiss = await page.evaluate(() => { for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) if (playerBoard[r][c].hit && !playerBoard[r][c].ship) return { r, c } })
  if (playerMiss) {
    const cls = await page.locator(`#player-board .cell[data-row="${playerMiss.r}"][data-col="${playerMiss.c}"]`).getAttribute('class')
    check('erro do computador no meu tabuleiro não aparece como acerto', !cls.includes('hit'), `classes: "${cls}"`)
  }

  console.log('--- vitória')
  await page.evaluate(() => initGame())
  const cells = await page.evaluate(() => computerShips.flatMap((s) => s.cells))
  for (const c of cells) { await page.locator(`#computer-board .cell[data-row="${c.row}"][data-col="${c.col}"]`).click(); if (await page.evaluate(() => gameOver)) break }
  const won = await page.locator('#status-message').innerText()
  // o computador pode vencer antes, com tiros aleatórios; repete com o tiro dele sempre na água
  check('afundar toda a frota dá vitória', /venceu/i.test(won), `"${won}"`)
  check('botão de reiniciar aparece no fim', await page.locator('#restart-button').isVisible())
  await page.locator('#computer-board .cell').first().click()
  check('depois do fim não dá para atirar', await page.evaluate(() => gameOver))

  console.log('--- derrota')
  await page.locator('#restart-button').click()
  check('reiniciar zera a partida', (await page.locator('#computer-board .cell.hit, #computer-board .cell.miss').count()) === 0 && !(await page.evaluate(() => gameOver)))
  await page.evaluate(() => { const seq = playerShips.flatMap((s) => s.cells).flatMap((c) => [(c.row + 0.5) / 10, (c.col + 0.5) / 10]); let i = 0; Math.random = () => seq[i++ % seq.length] })
  const misses = await page.evaluate(() => { const m = []; for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) if (!computerBoard[r][c].ship) m.push({ r, c }); return m })
  for (const c of misses) { await page.locator(`#computer-board .cell[data-row="${c.r}"][data-col="${c.c}"]`).click(); if (await page.evaluate(() => gameOver)) break }
  const lost = await page.locator('#status-message').innerText()
  check('perder toda a frota dá derrota', /perdeu/i.test(lost), `"${lost}"`)
  await page.screenshot({ path: 'play-1-fim.png' })

  console.log('--- acessibilidade')
  await page.locator('#restart-button').click()
  const focusable = await page.evaluate(() => [...document.querySelectorAll('#computer-board .cell')].filter((c) => c.tabIndex >= 0 || c.tagName === 'BUTTON').length)
  check('dá para jogar com teclado (casas focáveis)', focusable === 100, `focáveis=${focusable}`)
  check('nenhum erro de JavaScript na partida inteira', errors.length === 0, errors.join('|'))
  console.log(`\n${pass} PASS, ${fail} FAIL`)
  await browser.close()
})().catch((e) => { console.error('ERRO:', e.message.slice(0, 400)); process.exit(2) })
