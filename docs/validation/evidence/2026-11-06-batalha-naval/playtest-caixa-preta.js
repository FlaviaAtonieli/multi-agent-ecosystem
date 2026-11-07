// Testa uma batalha naval gerada por IA só pelo que aparece na tela, sem ler as
// variáveis internas do jogo (cada geração usa nomes diferentes).
//
// Uso: node playtest-caixa-preta.js <pasta-com-index.html>
// Requer playwright-core e um Chrome instalado.
const { chromium } = require('playwright-core')
const path = require('path')
const { pathToFileURL } = require('url')

const folder = process.argv[2] || path.join(__dirname, 'jogo-gerado')
const URL = pathToFileURL(path.resolve(folder, 'index.html')).href
const END = /venceu|vit[oó]ria|ganhou|parab[eé]ns|perdeu|derrota/i
// "Você perdeu! O computador venceu." tem "venceu": a derrota é conferida primeiro.
const LOSS = /perdeu|derrota/i
const results = []
const check = (label, ok, extra = '') => {
  results.push(ok)
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}${extra ? ` (${extra})` : ''}`)
}

// Math.random previsível, para repetir as partidas.
const seeded = (seed) => {
  let a = seed >>> 0
  Math.random = () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// Acha os dois tabuleiros: elementos com 100 filhos "iguais" (mesma tag e classe base).
async function boards(page) {
  return page.evaluate(() => {
    const found = []
    for (const el of document.querySelectorAll('body *')) {
      const groups = {}
      for (const child of el.children) {
        const key = child.tagName + '.' + (child.classList[0] || '')
        ;(groups[key] = groups[key] || []).push(child)
      }
      for (const group of Object.values(groups)) {
        if (group.length === 100) {
          group.forEach((cell, index) => cell.setAttribute('data-qa-cell', `${found.length}-${index}`))
          found.push(found.length)
        }
      }
    }
    return found.length
  })
}

// Muitos jogos recriam as casas a cada jogada: marca de novo antes de cada leitura.
const signature = async (page, board) => {
  await boards(page)
  return page.evaluate((b) =>
    [...document.querySelectorAll(`[data-qa-cell^="${b}-"]`)].map((cell) => {
      const style = getComputedStyle(cell)
      return [style.backgroundColor, style.backgroundImage, style.color, cell.textContent.trim()].join('|')
    }), board)
}

const majority = (list) => {
  const counts = {}
  list.forEach((value) => (counts[value] = (counts[value] || 0) + 1))
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0]
}

const pageText = (page) => page.evaluate(() => document.body.innerText)

async function newGame(browser, seed, errors) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
  await page.addInitScript(seeded, seed)
  await page.goto(URL)
  await page.waitForTimeout(300)
  const count = await boards(page)
  // O tabuleiro do computador é o que não mostra navios: todas as casas iguais no início.
  const first = await signature(page, 0)
  const second = count > 1 ? await signature(page, 1) : []
  const enemy = new Set(first).size === 1 ? 0 : 1
  const mine = enemy === 0 ? 1 : 0
  return { page, count, enemy, mine }
}

const cell = (page, board, index) => ({
  click: async (options) => { await boards(page); return page.locator(`[data-qa-cell="${board}-${index}"]`).click(options) },
  focus: async () => { await boards(page); return page.locator(`[data-qa-cell="${board}-${index}"]`).focus() },
})

// Atira em ordem embaralhada (pela semente) até o jogo anunciar o fim.
async function playToEnd(page, enemy, seed = 0) {
  const order = [...Array(100).keys()]
  let a = seed + 7
  for (let i = order.length - 1; i > 0; i--) {
    a = (a * 1103515245 + 12345) % 2147483648
    const j = a % (i + 1)
    ;[order[i], order[j]] = [order[j], order[i]]
  }
  for (let i = 0; i < 100; i++) {
    await cell(page, enemy, order[i]).click({ timeout: 2000 }).catch(() => {})
    const text = await pageText(page)
    if (END.test(text)) return { text, shots: i + 1 }
  }
  return { text: await pageText(page), shots: 100 }
}

;(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  const errors = []

  console.log('--- abre e monta')
  let { page, count, enemy, mine } = await newGame(browser, 1, errors)
  check('abre sem erro de JavaScript', errors.length === 0, errors.join(' | ').slice(0, 120))
  check('dois tabuleiros de 100 casas', count === 2, `achados: ${count}`)
  if (count !== 2) { console.log(`\n${results.filter(Boolean).length} de ${results.length}`); await browser.close(); return }
  const start = await signature(page, mine)
  const water = majority(start)
  check('17 casas de navio visíveis no meu tabuleiro', start.filter((s) => s !== water).length === 17,
    `${start.filter((s) => s !== water).length}`)
  check('navios do computador escondidos', new Set(await signature(page, enemy)).size === 1)

  console.log('--- tiro')
  const before = await pageText(page)
  const enemyBefore = await signature(page, enemy)
  await cell(page, enemy, 0).click()
  const enemyAfter = await signature(page, enemy)
  check('a casa atingida muda na tela', enemyAfter[0] !== enemyBefore[0])
  const after = await pageText(page)
  const newLines = after.split('\n').map((l) => l.trim()).filter((l) => l && !before.includes(l))
  const own = newLines.filter((l) => !/computador|inimigo|advers/i.test(l) && /acert|água|agua|err|afund|tiro|hit|miss/i.test(l))
  check('o jogador vê o resultado do próprio tiro', own.length > 0, newLines.join(' / ').slice(0, 140))
  const mineAfterOne = await signature(page, mine)
  const changedOne = mineAfterOne.filter((s, i) => s !== start[i]).length
  check('o computador responde com um tiro', changedOne === 1, `casas mudadas: ${changedOne}`)
  await cell(page, enemy, 0).click()
  const changedTwo = (await signature(page, mine)).filter((s, i) => s !== start[i]).length
  check('tiro repetido na mesma casa é ignorado', changedTwo === changedOne)

  console.log('--- partida inteira')
  const end = await playToEnd(page, enemy)
  check('a partida termina e anuncia o resultado', END.test(end.text), `${end.shots} tiros`)
  const finalMine = await signature(page, mine)
  const hitShip = new Set(), hitWater = new Set()
  finalMine.forEach((s, i) => { if (s !== start[i]) (start[i] === water ? hitWater : hitShip).add(s) })
  const overlap = [...hitWater].filter((s) => hitShip.has(s))
  // Acerto em navio que não muda nada na tela também é falha: o jogador não vê que foi atingido.
  check('erro e acerto do computador aparecem diferentes', hitWater.size > 0 && hitShip.size > 0 && overlap.length === 0,
    `casas de água atingidas com ${hitWater.size} aparência(s), casas de navio atingidas com ${hitShip.size}, iguais ${overlap.length}`)
  const frozen = await signature(page, enemy)
  await cell(page, enemy, 99).click().catch(() => {})
  check('depois do fim não dá para atirar', JSON.stringify(await signature(page, enemy)) === JSON.stringify(frozen))
  const restart = page.getByRole('button', { name: /reinici|novo jogo|jogar novamente|recome/i })
  const hasRestart = (await restart.count()) > 0 && (await restart.first().isVisible())
  check('aparece um botão para jogar de novo', hasRestart)
  if (hasRestart) {
    await restart.first().click()
    await page.waitForTimeout(200)
    await boards(page)
    check('reiniciar limpa a partida', new Set(await signature(page, enemy)).size === 1 && !END.test(await pageText(page)))
  } else {
    check('reiniciar limpa a partida', false, 'sem botão')
  }
  await page.close()

  console.log('--- teclado')
  ;({ page, enemy, mine } = await newGame(browser, 2, errors))
  const focusable = await page.evaluate((b) =>
    [...document.querySelectorAll(`[data-qa-cell^="${b}-"]`)].filter((c) => c.tabIndex >= 0 || c.tagName === 'BUTTON').length, enemy)
  check('casas do computador recebem foco pelo teclado', focusable === 100, `focáveis: ${focusable}`)
  const keyStart = await signature(page, enemy)
  await cell(page, enemy, 5).focus().catch(() => {})
  await page.keyboard.press('Enter')
  await page.waitForTimeout(100)
  check('Enter na casa focada dispara o tiro', (await signature(page, enemy))[5] !== keyStart[5])
  await page.close()

  console.log('--- vitória e derrota em partidas diferentes')
  let wins = 0, losses = 0
  for (let seed = 10; seed < 50 && !(wins && losses); seed++) {
    const game = await newGame(browser, seed, errors)
    const result = await playToEnd(game.page, game.enemy, seed)
    if (END.test(result.text)) LOSS.test(result.text) ? losses++ : wins++
    await game.page.close()
  }
  check('vitória e derrota acontecem e são anunciadas', wins > 0 && losses > 0, `vitórias ${wins}, derrotas ${losses}`)
  check('nenhum erro de JavaScript em todas as partidas', errors.length === 0, errors.join(' | ').slice(0, 120))

  console.log(`\n${results.filter(Boolean).length} de ${results.length}`)
  await browser.close()
})().catch((e) => { console.error('ERRO:', e.message.slice(0, 400)); process.exit(2) })
