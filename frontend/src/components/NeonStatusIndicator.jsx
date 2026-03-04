import { useState, useEffect } from 'react'
import { API_BASE } from '../api'

export default function NeonStatusIndicator() {
  const [status, setStatus] = useState('active')

  useEffect(() => {
    const check = () => {
      fetch(`${API_BASE}/api/health`)
        .then((r) => r.ok ? setStatus('active') : setStatus('error'))
        .catch(() => setStatus('error'))
    }
    check()
    const id = setInterval(check, 30000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="neon-status">
      <span className={`neon-dot ${status}`} />
      <span className={`neon-label ${status}`}>
        {status === 'active' ? 'ONLINE' : 'OFFLINE'}
      </span>
    </div>
  )
}
