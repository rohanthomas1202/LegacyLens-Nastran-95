import { useState } from 'react'
import { apiPost } from '../api'
import Autocomplete from './Autocomplete'

export default function CallSimulator() {
  const [entry, setEntry] = useState('NASTRN')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [playing, setPlaying] = useState(false)

  const simulate = async () => {
    if (!entry.trim()) return
    setLoading(true)
    setCurrentStep(0)
    setPlaying(false)
    try {
      const res = await apiPost('/api/simulate', { entry_point: entry, max_steps: 200 })
      setData(res)
    } catch (e) {
      setData({ error: e.message })
    } finally {
      setLoading(false)
    }
  }

  const play = () => {
    if (!data || playing) return
    setPlaying(true)
    let step = currentStep
    const interval = setInterval(() => {
      step++
      if (step >= data.steps.length) {
        clearInterval(interval)
        setPlaying(false)
        return
      }
      setCurrentStep(step)
    }, 150)
    return () => clearInterval(interval)
  }

  const step = data?.steps?.[currentStep]

  return (
    <div className="result-block">
      <h3>Call Stack Simulator</h3>
      <p className="muted">Step through execution flow from an entry point</p>
      <div className="flow-inputs" style={{ marginBottom: 16 }}>
        <div className="flow-field" style={{ flex: 1 }}>
          <Autocomplete value={entry} onChange={setEntry} placeholder="Entry point..." />
        </div>
        <button onClick={simulate} disabled={loading} className="flow-btn">
          {loading ? 'Simulating...' : 'Simulate'}
        </button>
      </div>

      {data && !data.error && (
        <>
          <div className="dead-code-stats" style={{ marginBottom: 12 }}>
            <span className="stat-pill">Steps: {data.total_steps}</span>
            <span className="stat-pill">Unique Routines: {data.unique_routines}</span>
            <span className="stat-pill">Max Depth: {data.max_depth}</span>
            {data.truncated && <span className="stat-pill dead">Truncated</span>}
          </div>

          <div className="sim-controls">
            <button onClick={() => setCurrentStep(Math.max(0, currentStep - 1))} disabled={currentStep === 0}>
              ◀ Prev
            </button>
            <button onClick={play} disabled={playing}>
              {playing ? '⏸ Playing...' : '▶ Play'}
            </button>
            <button onClick={() => setCurrentStep(Math.min(data.steps.length - 1, currentStep + 1))}
              disabled={currentStep >= data.steps.length - 1}>
              Next ▶
            </button>
            <span className="source-path">
              Step {currentStep + 1} / {data.steps.length}
            </span>
          </div>

          {step && (
            <div className="sim-current">
              <span className={`sim-action ${step.action}`}>{step.action === 'call' ? '→ CALL' : '← RETURN'}</span>
              <span className="dc-name">{step.name}</span>
              <span className="source-type">{step.chunk_type}</span>
              <span className="source-path">{step.file_path}:{step.start_line}</span>
              <span className="muted">depth: {step.depth}</span>
            </div>
          )}

          <div className="sim-stack">
            {data.steps.slice(Math.max(0, currentStep - 10), currentStep + 11).map((s, i) => {
              const actualIdx = Math.max(0, currentStep - 10) + i
              return (
                <div key={actualIdx}
                  className={`sim-step ${actualIdx === currentStep ? 'active' : ''} ${s.action}`}
                  onClick={() => setCurrentStep(actualIdx)}
                  style={{ paddingLeft: 12 + s.depth * 16 }}
                >
                  <span className="sim-step-num">{actualIdx + 1}</span>
                  <span className={`sim-action ${s.action}`}>{s.action === 'call' ? '→' : '←'}</span>
                  <span>{s.name}</span>
                </div>
              )
            })}
          </div>
        </>
      )}

      {data?.error && <div className="error-msg">Error: {data.error}</div>}
    </div>
  )
}
