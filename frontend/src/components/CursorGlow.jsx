import { useEffect, useRef } from 'react'

export default function CursorGlow() {
  const ref = useRef(null)
  const pos = useRef({ x: -999, y: -999 })
  const rendered = useRef({ x: -999, y: -999 })
  const raf = useRef(null)

  useEffect(() => {
    const el = ref.current

    const onMove = (e) => {
      pos.current.x = e.clientX
      pos.current.y = e.clientY
    }
    const onLeave = () => {
      pos.current.x = -999
      pos.current.y = -999
    }

    const lerp = (a, b, t) => a + (b - a) * t

    const tick = () => {
      rendered.current.x = lerp(rendered.current.x, pos.current.x, 1)
      rendered.current.y = lerp(rendered.current.y, pos.current.y, 1)
      el.style.transform = `translate(${rendered.current.x - 350}px, ${rendered.current.y - 350}px)`
      raf.current = requestAnimationFrame(tick)
    }

    window.addEventListener('mousemove', onMove)
    document.addEventListener('mouseleave', onLeave)
    raf.current = requestAnimationFrame(tick)

    return () => {
      window.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseleave', onLeave)
      cancelAnimationFrame(raf.current)
    }
  }, [])

  return (
    <div
      ref={ref}
      style={{
        position: 'fixed',
        width: 700,
        height: 700,
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(0,242,255,0.035) 0%, rgba(255,0,229,0.015) 35%, transparent 60%)',
        pointerEvents: 'none',
        zIndex: 0,
        willChange: 'transform',
        filter: 'blur(40px)',
      }}
    />
  )
}
