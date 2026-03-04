import { useState, useEffect, useRef } from 'react'

function generatePath(width, height, points) {
  const step = width / (points.length - 1)
  const padding = height * 0.1
  const usableHeight = height - padding * 2

  return points.map((p, i) => {
    const x = i * step
    const y = padding + usableHeight * (1 - p)
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
  }).join(' ')
}

function generateBars(width, height, count) {
  const barWidth = width / count
  return Array.from({ length: count }, (_, i) => ({
    x: i * barWidth,
    width: barWidth * 0.6,
    height: height * (0.1 + Math.random() * 0.35),
    y: height,
  }))
}

export default function AnimatedSparkline({ width = 300, height = 80 }) {
  const [frame, setFrame] = useState(0)
  const rafRef = useRef()
  const startRef = useRef(Date.now())

  useEffect(() => {
    const tick = () => {
      const elapsed = Date.now() - startRef.current
      setFrame(Math.floor(elapsed / 2000))
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [])

  const pointCount = 20
  const seed = frame
  const points = Array.from({ length: pointCount }, (_, i) => {
    const base = 0.3 + 0.4 * Math.sin((i + seed) * 0.5)
    const noise = 0.15 * Math.sin((i + seed) * 1.7) + 0.1 * Math.cos((i + seed) * 2.3)
    return Math.max(0, Math.min(1, base + noise))
  })

  const path = generatePath(width, height, points)
  const bars = generateBars(width, height, 12)

  return (
    <div className="sparkline-container">
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id="sparkline-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00f2ff" />
            <stop offset="100%" stopColor="#ff00e5" />
          </linearGradient>
        </defs>

        {bars.map((bar, i) => (
          <rect
            key={i}
            className="sparkline-bar"
            x={bar.x}
            y={bar.y - bar.height}
            width={bar.width}
            height={bar.height}
            rx={2}
          />
        ))}

        <path
          className="sparkline-path"
          d={path}
          style={{ transition: 'd 0.8s cubic-bezier(0.16, 1, 0.3, 1)' }}
        />
      </svg>
    </div>
  )
}
