import { useState } from 'react'
import { apiPost } from '../api'
import Autocomplete from './Autocomplete'

export default function ImpactPanel() {
  const [name, setName] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  const analyze = async () => {
    if (!name.trim()) return
    setLoading(true)
    try {
      const res = await apiPost('/api/impact', { name })
      setData(res)
    } catch (e) {
      setData({ error: e.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="result-block">
      <h3>Impact Analysis</h3>
      <p className="muted">What breaks if you change a routine?</p>
      <div className="flow-inputs" style={{ marginBottom: 16 }}>
        <div className="flow-field" style={{ flex: 1 }}>
          <Autocomplete value={name} onChange={setName} placeholder="Routine to change..." />
        </div>
        <button onClick={analyze} disabled={loading} className="flow-btn">
          {loading ? 'Analyzing...' : 'Analyze Impact'}
        </button>
      </div>

      {data && !data.error && (
        <div className="impact-results">
          <div className="dead-code-stats" style={{ marginBottom: 16 }}>
            <span className="stat-pill dead">Total Affected: {data.total_affected}</span>
            <span className="stat-pill">Max Depth: {data.max_depth_reached}</span>
            {data.common_block_impact.length > 0 && (
              <span className="stat-pill">COMMON Coupling: {data.common_block_impact.length}</span>
            )}
          </div>

          {data.impact_by_level.map(level => (
            <div key={level.depth} className="impact-level">
              <h4>{level.label} ({level.count})</h4>
              <div className="dep-list">
                {level.routines.map(r => (
                  <span key={r.name} className="dep-tag">
                    {r.name} <span className="source-path">{r.file_path}</span>
                  </span>
                ))}
              </div>
            </div>
          ))}

          {data.common_block_impact.length > 0 && (
            <div className="impact-level">
              <h4>COMMON Block Coupling ({data.common_block_impact.length})</h4>
              <div className="dep-list">
                {data.common_block_impact.map((r, i) => (
                  <span key={i} className="dep-tag">
                    {r.name} <span className="source-type">via /{r.block}/</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {data?.error && <div className="error-msg">Error: {data.error}</div>}
    </div>
  )
}
