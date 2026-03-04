import { useState } from 'react'
import { apiPost } from '../api'

export default function ComplexityPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sortBy, setSortBy] = useState('complexity_score')

  const load = async () => {
    setLoading(true)
    try {
      const res = await apiPost('/api/complexity', { top_n: 30 })
      setData(res)
    } catch (e) {
      setData({ error: e.message })
    } finally {
      setLoading(false)
    }
  }

  const sorted = data?.routines
    ? [...data.routines].sort((a, b) => b[sortBy] - a[sortBy])
    : []

  const columns = [
    { key: 'complexity_score', label: 'Score' },
    { key: 'loc', label: 'LOC' },
    { key: 'goto_count', label: 'GOTOs' },
    { key: 'call_count', label: 'CALLs' },
    { key: 'if_count', label: 'IFs' },
    { key: 'do_count', label: 'DOs' },
    { key: 'common_count', label: 'COMMON' },
  ]

  return (
    <div className="result-block">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>Code Complexity Metrics</h3>
        <button onClick={load} disabled={loading} className="feature-btn-sm">
          {loading ? 'Analyzing...' : data ? 'Refresh' : 'Analyze'}
        </button>
      </div>

      {data && !data.error && (
        <>
          <div className="dead-code-stats" style={{ marginBottom: 12 }}>
            <span className="stat-pill">Analyzed: {data.total_analyzed}</span>
            <span className="stat-pill">Avg LOC: {data.stats.avg_loc}</span>
            <span className="stat-pill dead">Most Complex: {data.stats.most_complex}</span>
          </div>

          <div className="dead-code-table-wrap">
            <table className="dead-code-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>File</th>
                  {columns.map(c => (
                    <th key={c.key}
                      onClick={() => setSortBy(c.key)}
                      style={{ cursor: 'pointer', textAlign: 'right', color: sortBy === c.key ? 'var(--cyan)' : undefined }}
                    >
                      {c.label} {sortBy === c.key ? '▾' : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((r, i) => (
                  <tr key={i}>
                    <td className="dc-name">{r.name}</td>
                    <td><span className="source-type">{r.chunk_type}</span></td>
                    <td className="source-path">{r.file_path}</td>
                    {columns.map(c => (
                      <td key={c.key} style={{ textAlign: 'right' }}>{r[c.key]}</td>
                    ))}
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
