import { useState } from 'react'
import { apiPost } from '../api'

export default function BatchModernizePanel() {
  const [mode, setMode] = useState('directory')
  const [directory, setDirectory] = useState('')
  const [names, setNames] = useState('')
  const [language, setLanguage] = useState('python')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [expandedResult, setExpandedResult] = useState({})

  const run = async () => {
    setLoading(true)
    setData(null)
    try {
      const body = { target_language: language }
      if (mode === 'directory') {
        body.directory = directory.trim()
      } else {
        body.names = names.split(/[,\s]+/).filter(Boolean)
      }
      const res = await apiPost('/api/modernize/batch', body)
      setData(res)
    } catch (e) {
      setData({ error: e.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="result-block">
      <h3>Batch Modernization</h3>
      <p className="muted">Translate multiple routines with dependency-aware ordering</p>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button onClick={() => setMode('directory')}
          className={mode === 'directory' ? 'feature-btn-sm active-toggle' : 'feature-btn-sm'}>
          By Directory
        </button>
        <button onClick={() => setMode('names')}
          className={mode === 'names' ? 'feature-btn-sm active-toggle' : 'feature-btn-sm'}>
          By Names
        </button>
      </div>

      <div className="flow-inputs" style={{ marginBottom: 16 }}>
        {mode === 'directory' ? (
          <input type="text" value={directory} onChange={e => setDirectory(e.target.value)}
            placeholder="Directory (e.g., mds, mis/mes)..." className="filter-input" style={{ flex: 1 }} />
        ) : (
          <input type="text" value={names} onChange={e => setNames(e.target.value)}
            placeholder="Routine names (comma-separated)..." className="filter-input" style={{ flex: 1 }} />
        )}
        <select value={language} onChange={e => setLanguage(e.target.value)} className="language-select">
          <option value="python">Python</option>
          <option value="c">C</option>
          <option value="java">Java</option>
          <option value="rust">Rust</option>
        </select>
        <button onClick={run} disabled={loading} className="flow-btn">
          {loading ? 'Translating...' : 'Run Batch'}
        </button>
      </div>

      {data && !data.error && (
        <>
          <div className="dead-code-stats" style={{ marginBottom: 12 }}>
            <span className="stat-pill">Total: {data.total_routines}</span>
            <span className="stat-pill alive">Success: {data.successful}</span>
            {data.failed > 0 && <span className="stat-pill dead">Failed: {data.failed}</span>}
          </div>

          {data.shared_state.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h4>Shared State (COMMON blocks between selected routines)</h4>
              <div className="dep-list">
                {data.shared_state.map((s, i) => (
                  <span key={i} className="dep-tag">/{s.block}/ ({s.count} routines)</span>
                ))}
              </div>
            </div>
          )}

          <h4>Migration Order</h4>
          <div className="batch-results">
            {data.results.map((r, i) => (
              <div key={i} className="common-block-card">
                <div className="common-block-header" onClick={() => setExpandedResult(prev => ({ ...prev, [r.name]: !prev[r.name] }))}>
                  <span className="expand-icon">{expandedResult[r.name] ? '▾' : '▸'}</span>
                  <span className="dc-name">{i + 1}. {r.name}</span>
                  <span className={`stat-pill ${r.status === 'success' ? 'alive' : 'dead'}`}>{r.status}</span>
                  <span className="source-path">{r.file_path}</span>
                </div>
                {expandedResult[r.name] && r.translated_code && (
                  <div className="batch-code">
                    <pre className="pattern-preview">{r.translated_code}</pre>
                    {r.migration_notes && (
                      <div style={{ padding: '8px 12px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {r.migration_notes}
                      </div>
                    )}
                  </div>
                )}
                {expandedResult[r.name] && r.error && (
                  <div className="error-msg" style={{ margin: 8 }}>{r.error}</div>
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
