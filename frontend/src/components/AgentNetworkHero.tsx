import { useEffect, useRef } from 'react'
import '../styles/agent-network.css'

type AgentNetworkHeroProps = {
  variant?: 'login' | 'register'
}

type NetworkNode = {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  hue: number
  hub: boolean
  phase: number
}

type PointerPosition = {
  x: number
  y: number
  active: boolean
}

const NODE_COLORS = [188, 205, 222, 252, 268]

function randomBetween(min: number, max: number) {
  return Math.random() * (max - min) + min
}

function createNodes(width: number, height: number): NetworkNode[] {
  const area = width * height
  const amount = Math.max(28, Math.min(68, Math.round(area / 17_000)))

  return Array.from({ length: amount }, (_, index) => ({
    x: randomBetween(18, Math.max(19, width - 18)),
    y: randomBetween(18, Math.max(19, height - 18)),
    vx: randomBetween(-0.18, 0.18),
    vy: randomBetween(-0.18, 0.18),
    radius: index % 11 === 0 ? randomBetween(3.2, 4.5) : randomBetween(1.5, 2.7),
    hue: NODE_COLORS[Math.floor(Math.random() * NODE_COLORS.length)],
    hub: index % 11 === 0,
    phase: randomBetween(0, Math.PI * 2),
  }))
}

export function AgentNetworkHero({ variant = 'login' }: AgentNetworkHeroProps) {
  const containerRef = useRef<HTMLElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const container = containerRef.current
    const canvas = canvasRef.current
    if (!container || !canvas) return

    const context = canvas.getContext('2d')
    if (!context) return

    const safeContainer: HTMLElement = container
    const safeCanvas: HTMLCanvasElement = canvas
    const safeContext: CanvasRenderingContext2D = context

    let width = 0
    let height = 0
    let nodes: NetworkNode[] = []
    let animationFrame = 0
    let lastFrame = performance.now()
    let reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const pointer: PointerPosition = { x: 0, y: 0, active: false }
    const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')

    function resizeCanvas() {
      const bounds = safeContainer.getBoundingClientRect()
      width = Math.max(1, bounds.width)
      height = Math.max(1, bounds.height)
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
      safeCanvas.width = Math.floor(width * pixelRatio)
      safeCanvas.height = Math.floor(height * pixelRatio)
      safeCanvas.style.width = `${width}px`
      safeCanvas.style.height = `${height}px`
      safeContext.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
      nodes = createNodes(width, height)
      draw(performance.now(), false)
    }

    function drawBackgroundGlow() {
      const gradient = safeContext.createRadialGradient(
        width * 0.5,
        height * 0.47,
        30,
        width * 0.5,
        height * 0.47,
        Math.max(width, height) * 0.62,
      )
      gradient.addColorStop(0, 'rgba(87, 70, 255, 0.14)')
      gradient.addColorStop(0.48, 'rgba(25, 191, 210, 0.06)')
      gradient.addColorStop(1, 'rgba(3, 7, 18, 0)')
      safeContext.fillStyle = gradient
      safeContext.fillRect(0, 0, width, height)
    }

    function drawConnections() {
      const connectionDistance = Math.min(160, Math.max(105, width * 0.17))
      for (let firstIndex = 0; firstIndex < nodes.length; firstIndex += 1) {
        const first = nodes[firstIndex]
        for (let secondIndex = firstIndex + 1; secondIndex < nodes.length; secondIndex += 1) {
          const second = nodes[secondIndex]
          const distance = Math.hypot(first.x - second.x, first.y - second.y)
          if (distance > connectionDistance) continue
          const opacity = (1 - distance / connectionDistance) * 0.34
          const gradient = safeContext.createLinearGradient(first.x, first.y, second.x, second.y)
          gradient.addColorStop(0, `hsla(${first.hue}, 92%, 68%, ${opacity})`)
          gradient.addColorStop(1, `hsla(${second.hue}, 92%, 68%, ${opacity})`)
          safeContext.beginPath()
          safeContext.moveTo(first.x, first.y)
          safeContext.lineTo(second.x, second.y)
          safeContext.strokeStyle = gradient
          safeContext.lineWidth = first.hub || second.hub ? 0.9 : 0.55
          safeContext.stroke()
        }
      }
    }

    function drawPointerConnections() {
      if (!pointer.active) return
      nodes.forEach((node) => {
        const distance = Math.hypot(pointer.x - node.x, pointer.y - node.y)
        if (distance > 170) return
        const opacity = (1 - distance / 170) * 0.38
        safeContext.beginPath()
        safeContext.moveTo(pointer.x, pointer.y)
        safeContext.lineTo(node.x, node.y)
        safeContext.strokeStyle = `rgba(106, 225, 232, ${opacity})`
        safeContext.lineWidth = 0.75
        safeContext.stroke()
      })
    }

    function drawNodes(time: number) {
      nodes.forEach((node) => {
        const pulse = node.hub ? 1 + Math.sin(time * 0.002 + node.phase) * 0.22 : 1
        const radius = node.radius * pulse
        if (node.hub) {
          safeContext.beginPath()
          safeContext.arc(node.x, node.y, radius * 4.3, 0, Math.PI * 2)
          safeContext.strokeStyle = `hsla(${node.hue}, 90%, 68%, 0.13)`
          safeContext.lineWidth = 1
          safeContext.stroke()
        }
        safeContext.beginPath()
        safeContext.arc(node.x, node.y, radius * 3.2, 0, Math.PI * 2)
        safeContext.fillStyle = `hsla(${node.hue}, 92%, 65%, ${node.hub ? 0.13 : 0.07})`
        safeContext.fill()
        safeContext.beginPath()
        safeContext.arc(node.x, node.y, radius, 0, Math.PI * 2)
        safeContext.fillStyle = `hsl(${node.hue}, 96%, ${node.hub ? 75 : 68}%)`
        safeContext.shadowBlur = node.hub ? 20 : 10
        safeContext.shadowColor = `hsla(${node.hue}, 96%, 68%, 0.85)`
        safeContext.fill()
        safeContext.shadowBlur = 0
      })
    }

    function updateNodes(delta: number) {
      const frameFactor = Math.min(delta / 16.67, 2)
      nodes.forEach((node) => {
        node.x += node.vx * frameFactor
        node.y += node.vy * frameFactor
        if (pointer.active) {
          const deltaX = pointer.x - node.x
          const deltaY = pointer.y - node.y
          const distance = Math.max(1, Math.hypot(deltaX, deltaY))
          if (distance < 150) {
            const attraction = (1 - distance / 150) * 0.003
            node.x += deltaX * attraction
            node.y += deltaY * attraction
          }
        }
        if (node.x <= 10 || node.x >= width - 10) {
          node.vx *= -1
          node.x = Math.min(Math.max(node.x, 10), width - 10)
        }
        if (node.y <= 10 || node.y >= height - 10) {
          node.vy *= -1
          node.y = Math.min(Math.max(node.y, 10), height - 10)
        }
      })
    }

    function draw(time: number, animate = true) {
      const delta = time - lastFrame
      lastFrame = time
      safeContext.clearRect(0, 0, width, height)
      drawBackgroundGlow()
      drawConnections()
      drawPointerConnections()
      drawNodes(time)
      if (animate && !reducedMotion) {
        updateNodes(delta)
        animationFrame = requestAnimationFrame((nextTime) => draw(nextTime))
      }
    }

    function startAnimation() {
      cancelAnimationFrame(animationFrame)
      lastFrame = performance.now()
      if (reducedMotion) {
        draw(lastFrame, false)
        return
      }
      animationFrame = requestAnimationFrame((time) => draw(time))
    }

    function handlePointerMove(event: PointerEvent) {
      const bounds = safeContainer.getBoundingClientRect()
      pointer.x = event.clientX - bounds.left
      pointer.y = event.clientY - bounds.top
      pointer.active = true
    }

    function handlePointerLeave() { pointer.active = false }
    function handleReducedMotionChange(event: MediaQueryListEvent) {
      reducedMotion = event.matches
      startAnimation()
    }

    const resizeObserver = new ResizeObserver(() => {
      resizeCanvas()
      startAnimation()
    })
    resizeObserver.observe(safeContainer)
    safeContainer.addEventListener('pointermove', handlePointerMove)
    safeContainer.addEventListener('pointerleave', handlePointerLeave)
    reducedMotionQuery.addEventListener('change', handleReducedMotionChange)
    resizeCanvas()
    startAnimation()

    return () => {
      cancelAnimationFrame(animationFrame)
      resizeObserver.disconnect()
      safeContainer.removeEventListener('pointermove', handlePointerMove)
      safeContainer.removeEventListener('pointerleave', handlePointerLeave)
      reducedMotionQuery.removeEventListener('change', handleReducedMotionChange)
    }
  }, [])

  return (
    <section ref={containerRef} className={`auth-hero network-hero network-hero-${variant}`}>
      <canvas ref={canvasRef} className="agent-network-canvas" aria-hidden="true" />
      <div className="network-noise" aria-hidden="true" />
      <div className="network-copy">
        <span className="network-kicker">ECOSSISTEMA MODULAR E RASTREÁVEL</span>
        <h1>
          <span>multi-agent</span>
          <strong>ecosystem</strong>
        </h1>
        <p>Arquitetura de Integração de Agentes Especialistas em Ambientes Corporativos</p>
      </div>
    </section>
  )
}
