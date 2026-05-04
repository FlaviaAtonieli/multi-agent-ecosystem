import { useEffect, useMemo, useRef, useState } from 'react'

const COLORS = [
  '#ffffff',
  '#6ee7ff',
  '#3b82f6',
  '#60a5fa',
  '#38bdf8',
  '#a78bfa',
  '#ff4fa3',
  '#ff8a3d',
  '#b7ff3c',
]

function lerp(a, b, t) {
  return a + (b - a) * t
}

function hexToRgb(hex) {
  const clean = hex.replace('#', '')
  const bigint = parseInt(clean, 16)

  return {
    r: (bigint >> 16) & 255,
    g: (bigint >> 8) & 255,
    b: bigint & 255
  }
}

function rgbToHex(r, g, b) {
  const toHex = value =>
    Math.max(0, Math.min(255, Math.round(value)))
      .toString(16)
      .padStart(2, '0')

  return `#${toHex(r)}${toHex(g)}${toHex(b)}`
}

function mixColors(colorA, colorB, t) {
  const a = hexToRgb(colorA)
  const b = hexToRgb(colorB)

  return rgbToHex(
    lerp(a.r, b.r, t),
    lerp(a.g, b.g, t),
    lerp(a.b, b.b, t)
  )
}

function distance(x1, y1, x2, y2) {
  const dx = x2 - x1
  const dy = y2 - y1
  return Math.sqrt(dx * dx + dy * dy)
}

export default function NeuralNetwork() {
  const canvasRef = useRef(null)
  const animationRef = useRef(null)

  const [size, setSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight
  })

  const mouseRef = useRef({
    x: 0,
    y: 0,
    active: false
  })

  const nodes = useMemo(() => {
    const base = [
      { x: 0.09, y: 0.22, color: COLORS[1], radius: 5.5 },
      { x: 0.15, y: 0.40, color: COLORS[6], radius: 4.8 },
      { x: 0.13, y: 0.67, color: COLORS[0], radius: 4.7 },
      { x: 0.12, y: 0.90, color: COLORS[8], radius: 4.6 },

      { x: 0.28, y: 0.20, color: COLORS[2], radius: 5.1 },
      { x: 0.30, y: 0.38, color: COLORS[7], radius: 5.8 },
      { x: 0.27, y: 0.56, color: COLORS[3], radius: 5.2 },
      { x: 0.24, y: 0.76, color: COLORS[1], radius: 5.4 },
      { x: 0.28, y: 0.94, color: COLORS[8], radius: 4.8 },

      { x: 0.44, y: 0.13, color: COLORS[4], radius: 5.2 },
      { x: 0.47, y: 0.33, color: COLORS[0], radius: 5.7 },
      { x: 0.54, y: 0.50, color: COLORS[2], radius: 8.5 },
      { x: 0.50, y: 0.67, color: COLORS[6], radius: 6.0 },
      { x: 0.45, y: 0.87, color: COLORS[5], radius: 5.4 },

      { x: 0.64, y: 0.16, color: COLORS[7], radius: 5.2 },
      { x: 0.69, y: 0.36, color: COLORS[1], radius: 5.6 },
      { x: 0.67, y: 0.59, color: COLORS[0], radius: 5.0 },
      { x: 0.69, y: 0.82, color: COLORS[4], radius: 5.2 },

      { x: 0.87, y: 0.25, color: COLORS[2], radius: 5.0 },
      { x: 0.91, y: 0.50, color: COLORS[6], radius: 5.2 },
      { x: 0.87, y: 0.75, color: COLORS[8], radius: 5.3 },
      { x: 0.91, y: 0.88, color: COLORS[3], radius: 5.1 },
    ]

    return base.map((node, index) => ({
      ...node,
      id: index,
      phase: (index + 1) * 0.9,
      driftX: 8 + (index % 5) * 3,
      driftY: 10 + (index % 4) * 3,
    }))
  }, [])

  const connections = useMemo(
    () => [
      [0, 1], [1, 2], [2, 3],
      [0, 4], [1, 5], [1, 6], [2, 6], [2, 7], [3, 7], [3, 8],
      [4, 5], [5, 6], [6, 7], [7, 8],
      [4, 9], [4, 10], [5, 10], [5, 11], [6, 10], [6, 11], [6, 12], [7, 11], [7, 12], [7, 13], [8, 13],
      [9, 10], [10, 11], [11, 12], [12, 13],
      [9, 14], [10, 14], [10, 15], [11, 15], [11, 16], [12, 16], [12, 17], [13, 17],
      [14, 15], [15, 16], [16, 17],
      [14, 18], [15, 18], [15, 19], [16, 19], [16, 20], [17, 20], [17, 21],
      [18, 19], [19, 20], [20, 21],
      [0, 5], [1, 4], [2, 8], [5, 9], [7, 13], [10, 16], [11, 17], [6, 12], [15, 20], [11, 14], [12, 15], [12, 18], [8, 12], [3, 6]
    ],
    []
  )

  useEffect(() => {
    const handleResize = () => {
      setSize({
        width: window.innerWidth,
        height: window.innerHeight
      })
    }

    const handleMouseMove = event => {
      mouseRef.current.x = event.clientX
      mouseRef.current.y = event.clientY
      mouseRef.current.active = true
    }

    const handleMouseLeave = () => {
      mouseRef.current.active = false
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    let start = performance.now()

    const render = now => {
      const elapsed = (now - start) / 1000
      const dpr = window.devicePixelRatio || 1

      canvas.width = size.width * dpr
      canvas.height = size.height * dpr
      canvas.style.width = `${size.width}px`
      canvas.style.height = `${size.height}px`

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, size.width, size.height)

      const bg = ctx.createRadialGradient(
        size.width / 2,
        size.height / 2,
        80,
        size.width / 2,
        size.height / 2,
        Math.max(size.width, size.height) * 0.7
      )
      bg.addColorStop(0, 'rgba(8, 20, 45, 0.30)')
      bg.addColorStop(0.35, 'rgba(8, 10, 25, 0.18)')
      bg.addColorStop(0.7, 'rgba(5, 5, 10, 0.12)')
      bg.addColorStop(1, 'rgba(0, 0, 0, 1)')
      ctx.fillStyle = bg
      ctx.fillRect(0, 0, size.width, size.height)

      const mouse = mouseRef.current

      const animatedNodes = nodes.map(node => {
        const baseX =
          node.x * size.width + Math.sin(elapsed * 0.9 + node.phase) * node.driftX
        const baseY =
          node.y * size.height + Math.cos(elapsed * 0.8 + node.phase) * node.driftY

        let offsetX = 0
        let offsetY = 0

        if (mouse.active) {
          const dx = mouse.x - baseX
          const dy = mouse.y - baseY
          const dist = Math.sqrt(dx * dx + dy * dy)
          const maxDistance = 240

          if (dist < maxDistance) {
            const force = (1 - dist / maxDistance) * 18
            offsetX = (dx / (dist || 1)) * force
            offsetY = (dy / (dist || 1)) * force
          }
        }

        return {
          ...node,
          px: baseX + offsetX,
          py: baseY + offsetY,
        }
      })

      if (mouse.active) {
        const outerGlow = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, 260)
        outerGlow.addColorStop(0, 'rgba(255,255,255,0.08)')
        outerGlow.addColorStop(0.16, 'rgba(110,231,255,0.16)')
        outerGlow.addColorStop(0.34, 'rgba(59,130,246,0.14)')
        outerGlow.addColorStop(0.54, 'rgba(255,79,163,0.11)')
        outerGlow.addColorStop(0.72, 'rgba(167,139,250,0.09)')
        outerGlow.addColorStop(0.86, 'rgba(183,255,60,0.06)')
        outerGlow.addColorStop(1, 'rgba(0,0,0,0)')

        ctx.beginPath()
        ctx.arc(mouse.x, mouse.y, 260, 0, Math.PI * 2)
        ctx.fillStyle = outerGlow
        ctx.fill()

        const innerCore = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, 110)
        innerCore.addColorStop(0, 'rgba(255,255,255,0.15)')
        innerCore.addColorStop(0.22, 'rgba(110,231,255,0.18)')
        innerCore.addColorStop(0.48, 'rgba(255,79,163,0.10)')
        innerCore.addColorStop(0.78, 'rgba(59,130,246,0.05)')
        innerCore.addColorStop(1, 'rgba(0,0,0,0)')

        ctx.beginPath()
        ctx.arc(mouse.x, mouse.y, 110, 0, Math.PI * 2)
        ctx.fillStyle = innerCore
        ctx.fill()
      }

      for (const [aIndex, bIndex] of connections) {
        const a = animatedNodes[aIndex]
        const b = animatedNodes[bIndex]

        const pulse = (Math.sin(elapsed * 1.8 + (a.id + b.id) * 0.45) + 1) / 2
        const blend = mixColors(a.color, b.color, pulse)

        const lineGradient = ctx.createLinearGradient(a.px, a.py, b.px, b.py)
        lineGradient.addColorStop(0, `${a.color}18`)
        lineGradient.addColorStop(0.45, `${blend}cc`)
        lineGradient.addColorStop(1, `${b.color}18`)

        ctx.beginPath()
        ctx.moveTo(a.px, a.py)

        const controlX =
          (a.px + b.px) / 2 + Math.sin(elapsed * 1.2 + a.id) * 18
        const controlY =
          (a.py + b.py) / 2 + Math.cos(elapsed * 1.1 + b.id) * 18

        ctx.quadraticCurveTo(controlX, controlY, b.px, b.py)
        ctx.strokeStyle = lineGradient
        ctx.lineWidth = 1 + pulse * 1.7
        ctx.shadowBlur = 16 + pulse * 14
        ctx.shadowColor = blend
        ctx.stroke()

        const tracerCount = 2

        for (let i = 0; i < tracerCount; i++) {
          const offset = i * 0.45
          const tracerT =
            (elapsed * (0.16 + i * 0.03) + (a.id + b.id) * 0.021 + offset) % 1

          const tx =
            (1 - tracerT) * (1 - tracerT) * a.px +
            2 * (1 - tracerT) * tracerT * controlX +
            tracerT * tracerT * b.px

          const ty =
            (1 - tracerT) * (1 - tracerT) * a.py +
            2 * (1 - tracerT) * tracerT * controlY +
            tracerT * tracerT * b.py

          const tracerColor = mixColors(a.color, b.color, tracerT)

          const tracerGlow = ctx.createRadialGradient(tx, ty, 0, tx, ty, 12)
          tracerGlow.addColorStop(0, `${tracerColor}ff`)
          tracerGlow.addColorStop(0.35, `${tracerColor}cc`)
          tracerGlow.addColorStop(1, `${tracerColor}00`)

          ctx.beginPath()
          ctx.arc(tx, ty, 2.4 + i * 0.4, 0, Math.PI * 2)
          ctx.fillStyle = tracerGlow
          ctx.shadowBlur = 18
          ctx.shadowColor = tracerColor
          ctx.fill()
        }
      }

      if (mouse.active) {
        for (const node of animatedNodes) {
          const d = distance(mouse.x, mouse.y, node.px, node.py)

          if (d < 220) {
            const alpha = 1 - d / 220
            const glowColor = mixColors(node.color, '#6ee7ff', 0.35)
            const alphaHex = Math.max(0, Math.min(255, Math.round(alpha * 150)))
              .toString(16)
              .padStart(2, '0')

            ctx.beginPath()
            ctx.moveTo(mouse.x, mouse.y)
            ctx.lineTo(node.px, node.py)
            ctx.strokeStyle = `${glowColor}${alphaHex}`
            ctx.lineWidth = 0.8 + alpha * 1.6
            ctx.shadowBlur = 16
            ctx.shadowColor = glowColor
            ctx.stroke()
          }
        }
      }

      for (const node of animatedNodes) {
        const halo = 12 + Math.sin(elapsed * 2 + node.phase) * 4

        const radial = ctx.createRadialGradient(node.px, node.py, 1, node.px, node.py, halo)
        radial.addColorStop(0, `${node.color}ff`)
        radial.addColorStop(0.45, `${node.color}66`)
        radial.addColorStop(1, `${node.color}00`)

        ctx.beginPath()
        ctx.arc(node.px, node.py, halo, 0, Math.PI * 2)
        ctx.fillStyle = radial
        ctx.fill()

        ctx.beginPath()
        ctx.arc(
          node.px,
          node.py,
          node.radius + Math.sin(elapsed * 1.5 + node.phase) * 0.8,
          0,
          Math.PI * 2
        )
        ctx.fillStyle = node.color
        ctx.shadowBlur = 22
        ctx.shadowColor = node.color
        ctx.fill()
      }

      for (let i = 0; i < 70; i++) {
        const x = ((i * 173) % size.width) + Math.sin(elapsed * 0.25 + i) * 14
        const y = ((i * 113) % size.height) + Math.cos(elapsed * 0.22 + i) * 14
        const alpha = 0.025 + ((Math.sin(elapsed + i) + 1) / 2) * 0.05

        ctx.beginPath()
        ctx.arc(x, y, 1 + (i % 3) * 0.35, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(255,255,255,${alpha})`
        ctx.fill()
      }

      animationRef.current = requestAnimationFrame(render)
    }

    animationRef.current = requestAnimationFrame(render)

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [connections, nodes, size])

  return <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
}