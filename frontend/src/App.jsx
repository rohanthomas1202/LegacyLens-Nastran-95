import { useState } from 'react'
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter'
import fortran from 'react-syntax-highlighter/dist/esm/languages/hljs/fortran'
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs'
import './App.css'

SyntaxHighlighter.registerLanguage('fortran', fortran)

const API_BASE = import.meta.env.VITE_API_URL || ''

const SAMPLE_QUERIES = [
  'Where is the main entry point of this program?',
  'What functions handle stiffness matrix assembly?',
  'Explain the GINO I/O system',
  'Find all error handling patterns',
  'What are the dependencies of the NASTRN module?',
]

export default function App() {
  const [tab, setTab] = useState('query')

  // Query tab state
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState(null)
  const [sources, setSources] = useState([])
  const [queryTime, setQueryTime] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedSource, setExpandedSource] = useState(null)

  // Full file modal
  const [fullFile, setFullFile] = useState(null)

  // Code analysis tab state
  const [entityName, setEntityName] = useState('')
  const [activeFeature, setActiveFeature] = useState(null)
  const [featureResult, setFeatureResult] = useState(null)
  const [featureLoading, setFeatureLoading] = useState(false)

  // Stats tab state
  const [stats, setStats] = useState(null)

  // --- Query Tab ---
  const handleQuery = async (q) => {
    const queryText = q || query
    if (!queryText.trim()) return
    setLoading(true)
    setError(null)
    setAnswer(null)
    setSources([])

    try {
      const res = await fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText, top_k: 5 }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setAnswer(data.answer)
      setSources(data.sources || [])
      setQueryTime(data.query_time_ms)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const loadFullFile = async (filePath, startLine) => {
    try {
      const res = await fetch(`${API_BASE}/api/file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: filePath }),
      })
      if (!res.ok) throw new Error('File not found')
      const data = await res.json()
      setFullFile({ ...data, highlightStart: startLine })
    } catch (e) {
      alert(`Could not load file: ${e.message}`)
    }
  }

  // --- Code Analysis Tab ---
  const handleFeature = async (feature) => {
    if (!entityName.trim()) return
    setActiveFeature(feature)
    setFeatureLoading(true)
    setFeatureResult(null)

    const endpointMap = {
      explain: '/api/explain',
      dependencies: '/api/dependencies',
      patterns: '/api/patterns',
      'generate-docs': '/api/generate-docs',
      'business-rules': '/api/business-rules',
    }

    try {
      const res = await fetch(`${API_BASE}${endpointMap[feature]}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: entityName }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setFeatureResult(data)
    } catch (e) {
      setFeatureResult({ error: e.message })
    } finally {
      setFeatureLoading(false)
    }
  }

  // --- Stats Tab ---
  const loadStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/stats`)
      const data = await res.json()
      setStats(data)
    } catch (e) {
      setStats({ error: e.message })
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>LegacyLens</h1>
        <p className="subtitle">NASTRAN-95 Code Intelligence</p>
      </header>

      <nav className="tabs">
        <button className={tab === 'query' ? 'active' : ''} onClick={() => setTab('query')}>Query</button>
        <button className={tab === 'analysis' ? 'active' : ''} onClick={() => setTab('analysis')}>Code Analysis</button>
        <button className={tab === 'stats' ? 'active' : ''} onClick={() => { setTab('stats'); loadStats() }}>Stats</button>
      </nav>

      <main className="content">
        {/* ========== QUERY TAB ========== */}
        {tab === 'query' && (
          <div className="query-tab">
            <div className="query-input">
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask a question about the NASTRAN-95 codebase..."
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleQuery() } }}
              />
              <button onClick={() => handleQuery()} disabled={loading}>
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>

            <div className="sample-queries">
              {SAMPLE_QUERIES.map((q, i) => (
                <button key={i} onClick={() => { setQuery(q); handleQuery(q) }} className="sample-btn">{q}</button>
              ))}
            </div>

            {error && <div className="error-msg">Error: {error}</div>}

            {answer && (
              <div className="answer-section">
                <h3>Answer {queryTime && <span className="timing">({queryTime}ms)</span>}</h3>
                <div className="answer-text">
                  {answer.split('\n').map((line, i) => {
                    if (line.startsWith('## ')) return <h4 key={i}>{line.replace('## ', '')}</h4>
                    if (line.startsWith('**') && line.endsWith('**')) return <strong key={i}>{line.replace(/\*\*/g, '')}<br/></strong>
                    if (line.startsWith('- ')) return <li key={i}>{line.replace('- ', '')}</li>
                    if (line.trim() === '') return <br key={i} />
                    return <p key={i}>{line}</p>
                  })}
                </div>
              </div>
            )}

            {sources.length > 0 && (
              <div className="sources-section">
                <h3>Sources ({sources.length})</h3>
                {sources.map((source, i) => (
                  <div key={i} className="source-card">
                    <div className="source-header" onClick={() => setExpandedSource(expandedSource === i ? null : i)}>
                      <div className="source-info">
                        <span className="source-name">{source.name}</span>
                        <span className="source-type">{source.chunk_type}</span>
                        <span className="source-path">{source.file_path}:{source.start_line}-{source.end_line}</span>
                      </div>
                      <div className="source-actions">
                        <span className="score-badge">{(source.score * 100).toFixed(0)}%</span>
                        <button
                          className="view-file-btn"
                          onClick={(e) => { e.stopPropagation(); loadFullFile(source.file_path, source.start_line) }}
                        >
                          View File
                        </button>
                        <span className="expand-icon">{expandedSource === i ? '▼' : '▶'}</span>
                      </div>
                    </div>
                    {expandedSource === i && (
                      <SyntaxHighlighter
                        language="fortran"
                        style={atomOneDark}
                        showLineNumbers={true}
                        startingLineNumber={source.start_line || 1}
                        customStyle={{ margin: 0, borderRadius: 0, borderTop: '1px solid #2a2a3a', fontSize: '0.85rem' }}
                      >
                        {source.content || '// No content available'}
                      </SyntaxHighlighter>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ========== CODE ANALYSIS TAB ========== */}
        {tab === 'analysis' && (
          <div className="analysis-tab">
            <div className="entity-input">
              <input
                type="text"
                value={entityName}
                onChange={(e) => setEntityName(e.target.value)}
                placeholder="Enter entity name (e.g., NASTRN, SDR2A, DPSE4)"
                onKeyDown={(e) => { if (e.key === 'Enter') handleFeature('explain') }}
              />
            </div>

            <div className="feature-buttons">
              <button onClick={() => handleFeature('explain')} disabled={featureLoading}>Explain Code</button>
              <button onClick={() => handleFeature('dependencies')} disabled={featureLoading}>Map Dependencies</button>
              <button onClick={() => handleFeature('patterns')} disabled={featureLoading}>Find Patterns</button>
              <button onClick={() => handleFeature('generate-docs')} disabled={featureLoading}>Generate Docs</button>
              <button onClick={() => handleFeature('business-rules')} disabled={featureLoading}>Extract Rules</button>
            </div>

            {featureLoading && <div className="loading">Analyzing...</div>}

            {featureResult && !featureLoading && (
              <div className="feature-result">
                {featureResult.error ? (
                  <div className="error-msg">Error: {featureResult.error}</div>
                ) : (
                  <>
                    {/* Explain */}
                    {activeFeature === 'explain' && featureResult.explanation && (
                      <div className="result-block">
                        <h3>Explanation: {featureResult.name}</h3>
                        <div className="markdown-content">
                          {featureResult.explanation.split('\n').map((line, i) => {
                            if (line.startsWith('## ')) return <h4 key={i}>{line.replace('## ', '')}</h4>
                            if (line.startsWith('- ')) return <li key={i}>{line.replace('- ', '')}</li>
                            if (line.trim() === '') return <br key={i} />
                            return <p key={i}>{line}</p>
                          })}
                        </div>
                      </div>
                    )}

                    {/* Dependencies */}
                    {activeFeature === 'dependencies' && (
                      <div className="result-block">
                        <h3>Dependencies: {featureResult.name}</h3>
                        <div className="dep-section">
                          <h4>Calls / References ({featureResult.calls?.length || 0})</h4>
                          <div className="dep-list">
                            {featureResult.calls?.map((c, i) => (
                              <span key={i} className="dep-tag">{c}</span>
                            ))}
                          </div>
                        </div>
                        <div className="dep-section">
                          <h4>Called By ({featureResult.called_by?.length || 0})</h4>
                          {featureResult.called_by?.length > 0 ? (
                            <div className="dep-list">
                              {featureResult.called_by.map((c, i) => (
                                <span key={i} className="dep-tag">{c.name} ({c.file_path}:{c.start_line})</span>
                              ))}
                            </div>
                          ) : (
                            <p className="muted">No callers found in indexed code</p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Patterns */}
                    {activeFeature === 'patterns' && (
                      <div className="result-block">
                        <h3>Similar Patterns: {featureResult.name}</h3>
                        {featureResult.similar_patterns?.map((p, i) => (
                          <div key={i} className="pattern-card">
                            <div className="pattern-header">
                              <strong>{p.name}</strong>
                              <span className="source-path">{p.file_path}:{p.start_line}-{p.end_line}</span>
                              <span className="score-badge">{(p.similarity * 100).toFixed(0)}%</span>
                            </div>
                            <pre className="pattern-preview">{p.content_preview}</pre>
                          </div>
                        ))}
                        {(!featureResult.similar_patterns || featureResult.similar_patterns.length === 0) && (
                          <p className="muted">No similar patterns found</p>
                        )}
                      </div>
                    )}

                    {/* Generate Docs */}
                    {activeFeature === 'generate-docs' && featureResult.documentation && (
                      <div className="result-block">
                        <h3>Documentation: {featureResult.name}</h3>
                        <div className="markdown-content">
                          {featureResult.documentation.split('\n').map((line, i) => {
                            if (line.startsWith('## ')) return <h4 key={i}>{line.replace('## ', '')}</h4>
                            if (line.startsWith('### ')) return <h5 key={i}>{line.replace('### ', '')}</h5>
                            if (line.startsWith('- ')) return <li key={i}>{line.replace('- ', '')}</li>
                            if (line.trim() === '') return <br key={i} />
                            return <p key={i}>{line}</p>
                          })}
                        </div>
                      </div>
                    )}

                    {/* Business Rules */}
                    {activeFeature === 'business-rules' && featureResult.rules && (
                      <div className="result-block">
                        <h3>Business Rules: {featureResult.name}</h3>
                        <div className="markdown-content">
                          {featureResult.rules.split('\n').map((line, i) => {
                            if (line.startsWith('## ')) return <h4 key={i}>{line.replace('## ', '')}</h4>
                            if (line.startsWith('- **')) return <li key={i} dangerouslySetInnerHTML={{ __html: line.replace('- ', '').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
                            if (line.startsWith('- ')) return <li key={i}>{line.replace('- ', '')}</li>
                            if (line.trim() === '') return <br key={i} />
                            return <p key={i}>{line}</p>
                          })}
                        </div>
                      </div>
                    )}

                    {/* Sources */}
                    {featureResult.sources?.length > 0 && (
                      <div className="feature-sources">
                        <h4>Sources</h4>
                        {featureResult.sources.map((s, i) => (
                          <span key={i} className="source-ref">{s.name} - {s.file_path}:{s.start_line}-{s.end_line}</span>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* ========== STATS TAB ========== */}
        {tab === 'stats' && (
          <div className="stats-tab">
            {stats ? (
              stats.error ? (
                <div className="error-msg">Error: {stats.error}</div>
              ) : (
                <>
                  <div className="stats-grid">
                    <div className="stat-card">
                      <h3>Index</h3>
                      <div className="stat-value">{stats.index?.total_vectors?.toLocaleString()}</div>
                      <div className="stat-label">Total Vectors</div>
                      <div className="stat-detail">{stats.index?.dimension}d embeddings</div>
                    </div>

                    <div className="stat-card">
                      <h3>Queries</h3>
                      <div className="stat-value">{stats.costs?.query_count}</div>
                      <div className="stat-label">Total Queries</div>
                      <div className="stat-detail">{stats.costs?.ingestion_count} ingestions</div>
                    </div>

                    <div className="stat-card">
                      <h3>Total Cost</h3>
                      <div className="stat-value">${stats.costs?.total_cost?.toFixed(4)}</div>
                      <div className="stat-label">All API Costs</div>
                    </div>
                  </div>

                  <div className="cost-breakdown">
                    <h3>Cost Breakdown</h3>
                    <table>
                      <thead><tr><th>Category</th><th>Tokens</th><th>Cost</th></tr></thead>
                      <tbody>
                        <tr>
                          <td>Embeddings</td>
                          <td>{stats.costs?.embedding_tokens?.toLocaleString()}</td>
                          <td>${stats.costs?.embedding_cost?.toFixed(4)}</td>
                        </tr>
                        <tr>
                          <td>LLM Input</td>
                          <td>{stats.costs?.llm_input_tokens?.toLocaleString()}</td>
                          <td>${stats.costs?.llm_input_cost?.toFixed(4)}</td>
                        </tr>
                        <tr>
                          <td>LLM Output</td>
                          <td>{stats.costs?.llm_output_tokens?.toLocaleString()}</td>
                          <td>${stats.costs?.llm_output_cost?.toFixed(4)}</td>
                        </tr>
                      </tbody>
                      <tfoot>
                        <tr><td><strong>Total</strong></td><td></td><td><strong>${stats.costs?.total_cost?.toFixed(4)}</strong></td></tr>
                      </tfoot>
                    </table>
                  </div>
                </>
              )
            ) : (
              <div className="loading">Loading stats...</div>
            )}
          </div>
        )}
      </main>

      {/* ========== FULL FILE MODAL ========== */}
      {fullFile && (
        <div className="modal-overlay" onClick={() => setFullFile(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">{fullFile.file_path}</span>
              <span className="modal-lines">{fullFile.total_lines} lines</span>
              <button className="modal-close" onClick={() => setFullFile(null)}>Close</button>
            </div>
            <div className="modal-body">
              <SyntaxHighlighter
                language="fortran"
                style={atomOneDark}
                showLineNumbers={true}
                wrapLines={true}
                lineProps={(lineNumber) => {
                  const hl = fullFile.highlightStart
                  if (hl && lineNumber >= hl && lineNumber <= hl + 30) {
                    return { style: { backgroundColor: 'rgba(0, 212, 255, 0.08)' } }
                  }
                  return {}
                }}
                customStyle={{ margin: 0, fontSize: '0.85rem', background: '#141420' }}
              >
                {fullFile.content}
              </SyntaxHighlighter>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
