import { useState } from 'react'
import { apiPost } from '../api'

export default function XrefPanel() {
  const [variable, setVariable] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  const search = async () => {
    if (!variable.trim()) return
    setLoading(true)
    try {
      const res = await apiPost('/api/xref', { variable })
      setData(res)
    } catch (e) {
      setData({ error: e.message })
    } finally {
      setLoading(false)
    }
  }

  const accessColor = (access) => {
    if (access === 'write') return 'var(--magenta)'
    if (access === 'read-write') return 'var(--yellow, #ffd700)'
    return 'var(--cyan)'
  }

  return (
    <div className="result-block">
      <h3>Variable Cross-Reference</h3>
      <p className="muted">Find all routines that read or write a variable</p>
      <div className="flow-inputs" style={{ marginBottom: 16 }}>
        <input
          type="text"
          value={variable}
          onChange={e => setVariable(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
          placeholder="Variable name (e.g., CORE, IBUF)..."
          className="filter-input"
          style={{ flex: 1 }}
        />
        <button onClick={search} disabled={loading} className="flow-btn">
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {data && !data.error && (
        <>
          <div className="dead-code-stats" style={{ marginBottom: 12 }}>
            <span className="stat-pill">References: {data.total_references}</span>
            <span className="stat-pill" style={{ borderColor: 'var(--magenta)' }}>Writers: {data.writers}</span>
            <span className="stat-pill" style={{ borderColor: 'var(--cyan)' }}>Readers: {data.readers}</span>
            {data.common_blocks.length > 0 && (
              <span className="stat-pill">COMMON: {data.common_blocks.join(', ')}</span>
            )}
          </div>

          <div className="dead-code-table-wrap">
            <table className="dead-code-table">
              <thead><tr><th>Routine</th><th>Type</th><th>Access</th><th>File</th><th>Lines</th></tr></thead>
              <tbody>
                {data.references.map((r, i) => (
                  <tr key={i}>
                    <td className="dc-name">{r.name}</td>
                    <td><span className="source-type">{r.chunk_type}</span></td>
                    <td><span style={{ color: accessColor(r.access), fontWeight: 600 }}>{r.access}</span></td>
                    <td className="source-path">{r.file_path}</td>
                    <td>{r.start_line}-{r.end_line}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {data?.error && <div className="error-msg">Error: {data.error}</div>}
    </div>
  )
}
