import { useState, useEffect } from 'react'
import { apiFetch } from '../api'

export default function ArchitectureMap() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(null)
  const [sortBy, setSortBy] = useState('routine_count')
  const [filter, setFilter] = useState('')

  useEffect(() => {
    setLoading(true)
    apiFetch('/api/architecture')
      .then(setData)
      .catch(e => setData({ error: e.message }))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading">Loading architecture...</div>
  if (data?.error) return <div className="error-msg">Error: {data.error}</div>
  if (!data) return null

  const sorted = [...data.modules]
    .filter(m => !filter || m.name.toLowerCase().includes(filter.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name)
      return b[sortBy] - a[sortBy]
    })

  const maxRoutines = Math.max(...data.modules.map(m => m.routine_count))
  const sel = expanded ? data.modules.find(m => m.name === expanded) : null

  return (
    <div className="arch-layout">
      <div className="arch-overview">
        <div className="dead-code-stats" style={{ marginBottom: 12 }}>
          <span className="stat-pill">{data.total_modules} modules</span>
          <span className="stat-pill">{data.total_inter_module_edges} cross-module calls</span>
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
          <input type="text" value={filter} onChange={e => setFilter(e.target.value)}
            placeholder="Filter modules..." className="filter-input" style={{ flex: 1 }} />
          <select value={sortBy} onChange={e => setSortBy(e.target.value)} className="language-select">
            <option value="routine_count">By Size</option>
            <option value="internal_edges">By Internal Calls</option>
            <option value="name">By Name</option>
          </select>
        </div>

        <div className="arch-modules">
          {sorted.map(m => (
            <div key={m.name}
              className={`arch-module-card ${expanded === m.name ? 'selected' : ''}`}
              onClick={() => setExpanded(expanded === m.name ? null : m.name)}
            >
              <div className="arch-module-bar"
                style={{ width: `${(m.routine_count / maxRoutines) * 100}%` }} />
              <div className="arch-module-content">
                <span className="arch-module-name">{m.name}/</span>
                <span className="arch-module-count">{m.routine_count}</span>
                <div className="arch-module-types">
                  {Object.entries(m.types).map(([t, c]) => (
                    <span key={t} className="arch-type-tag">{t}: {c}</span>
                  ))}
                </div>
                {m.internal_edges > 0 && (
                  <span className="arch-internal">{m.internal_edges} internal calls</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {sel && (
        <div className="arch-detail">
          <div className="arch-detail-header">
            <h3>{sel.name}/</h3>
            <button onClick={() => setExpanded(null)} className="history-clear">Close</button>
          </div>

          {sel.connects_to.length > 0 && (
            <div className="arch-detail-section">
              <h4>Calls Into</h4>
              <div className="dep-list">
                {sel.connects_to.map(c => (
                  <span key={c.module} className="dep-tag"
                    onClick={() => setExpanded(c.module)} style={{ cursor: 'pointer' }}>
                    {c.module}/ <span className="source-type">{c.calls} calls</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="arch-detail-section">
            <h4>Routines ({sel.routines.length})</h4>
            <div className="dead-code-table-wrap" style={{ maxHeight: 400 }}>
              <table className="dead-code-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th style={{ textAlign: 'right' }}>Calls</th>
                    <th style={{ textAlign: 'right' }}>Called By</th>
                    <th>Lines</th>
                  </tr>
                </thead>
                <tbody>
                  {sel.routines.map(r => (
                    <tr key={r.name}>
                      <td className="dc-name">{r.name}</td>
                      <td><span className="source-type">{r.chunk_type}</span></td>
                      <td style={{ textAlign: 'right' }}>{r.calls_out}</td>
                      <td style={{ textAlign: 'right' }}>{r.called_by}</td>
                      <td className="source-path">{r.start_line}-{r.end_line}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
