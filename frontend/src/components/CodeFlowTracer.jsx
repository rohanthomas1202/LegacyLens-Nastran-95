import { useState } from 'react'
import { apiPost } from '../api'
import Autocomplete from './Autocomplete'

export default function CodeFlowTracer({ onSwitchToGraph }) {
  const [source, setSource] = useState('')
  const [target, setTarget] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleTrace = async () => {
    if (!source.trim() || !target.trim()) return
    setLoading(true)
    setResult(null)

    try {
      const data = await apiPost('/api/flow-trace', { source, target })
      setResult(data)
    } catch (e) {
      setResult({ error: e.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flow-tracer">
      <h3>Code Flow Tracer</h3>
      <p className="muted">Find the shortest call path between two routines</p>

      <div className="flow-inputs">
        <div className="flow-field">
          <label>From</label>
          <Autocomplete value={source} onChange={setSource} placeholder="Source routine..." />
        </div>
        <span className="flow-arrow">→</span>
        <div className="flow-field">
          <label>To</label>
          <Autocomplete value={target} onChange={setTarget} placeholder="Target routine..." />
        </div>
        <button onClick={handleTrace} disabled={loading} className="flow-btn">
          {loading ? 'Tracing...' : 'Trace'}
        </button>
      </div>

      {result && result.error && (
        <div className="error-msg">{result.error}</div>
      )}

      {result && result.path && result.path.length > 0 && (
        <div className="flow-result">
          <div className="flow-header">
            <span>Path found: {result.length} steps</span>
            {onSwitchToGraph && (
              <button className="view-file-btn" onClick={() => onSwitchToGraph(result.source)}>
                View in Graph
              </button>
            )}
          </div>
          <div className="flow-timeline">
            {result.path.map((step, i) => (
              <div key={i} className="flow-step">
                <div className="flow-step-marker">
                  <div className={`flow-dot ${i === 0 ? 'start' : i === result.path.length - 1 ? 'end' : ''}`} />
                  {i < result.path.length - 1 && <div className="flow-line" />}
                </div>
                <div className="flow-step-info">
                  <span className="flow-step-name">{step.name}</span>
                  <span className="source-type">{step.chunk_type}</span>
                  <span className="source-path">{step.file_path}:{step.start_line}-{step.end_line}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
