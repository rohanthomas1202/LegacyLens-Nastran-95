import { useState, useEffect } from 'react'
import { apiFetch } from '../api'

export default function CommonBlocksPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState({})
  const [search, setSearch] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const res = await apiFetch('/api/common-blocks')
      setData(res)
    } catch (e) {
      setData({ error: e.message })
    } finally {
      setLoading(false)
    }
  }

  const toggle = (name) => setExpanded(prev => ({ ...prev, [name]: !prev[name] }))

  const filtered = data?.blocks?.filter(b =>
    b.name.toLowerCase().includes(search.toLowerCase())
  ) || []

  return (
    <div className="result-block">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>COMMON Block Inspector</h3>
        <button onClick={load} disabled={loading} className="feature-btn-sm">
          {loading ? 'Loading...' : data ? 'Refresh' : 'Load Blocks'}
        </button>
      </div>

      {data && !data.error && (
        <>
          <div className="dead-code-stats" style={{ marginBottom: 12 }}>
            <span className="stat-pill">Blocks: {data.total_blocks}</span>
            <span className="stat-pill">Avg Routines: {data.stats.avg_routines_per_block}</span>
            <span className="stat-pill dead">Most Coupled: {data.stats.most_coupled_block} ({data.stats.max_coupling})</span>
          </div>

          <input
            type="text"
            placeholder="Filter blocks..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="filter-input"
          />

          <div className="common-blocks-list">
            {filtered.slice(0, 100).map(block => (
              <div key={block.name} className="common-block-card">
                <div className="common-block-header" onClick={() => toggle(block.name)}>
                  <span className="expand-icon">{expanded[block.name] ? '▾' : '▸'}</span>
                  <span className="dc-name">{block.name}</span>
                  <span className="stat-pill" style={{ fontSize: '0.65rem' }}>{block.routine_count} routines</span>
                  {block.variables.length > 0 && (
                    <span className="source-path" style={{ marginLeft: 'auto' }}>
                      vars: {block.variables.join(', ')}
                    </span>
                  )}
                </div>
                {expanded[block.name] && (
                  <div className="common-block-routines">
                    {block.routines.map(r => (
                      <span key={r.name} className="dep-tag">
                        {r.name} <span className="source-type">{r.chunk_type}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {data?.error && <div className="error-msg">Error: {data.error}</div>}
    </div>
  )
}
