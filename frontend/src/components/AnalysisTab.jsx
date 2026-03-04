import { useState } from 'react'
import { apiPost, apiFetch } from '../api'
import MarkdownContent from './MarkdownContent'
import Autocomplete from './Autocomplete'
import XrefPanel from './XrefPanel'

const ENDPOINT_MAP = {
  explain: '/api/explain',
  dependencies: '/api/dependencies',
  patterns: '/api/patterns',
  'generate-docs': '/api/generate-docs',
  'business-rules': '/api/business-rules',
}

export default function AnalysisTab() {
  const [entityName, setEntityName] = useState('')
  const [activeFeature, setActiveFeature] = useState(null)
  const [featureResult, setFeatureResult] = useState(null)
  const [featureLoading, setFeatureLoading] = useState(false)
  const [deadCode, setDeadCode] = useState(null)
  const [deadCodeLoading, setDeadCodeLoading] = useState(false)

  const handleFeature = async (feature) => {
    if (!entityName.trim()) return
    setActiveFeature(feature)
    setFeatureLoading(true)
    setFeatureResult(null)

    try {
      const data = await apiPost(ENDPOINT_MAP[feature], { name: entityName })
      setFeatureResult(data)
    } catch (e) {
      setFeatureResult({ error: e.message })
    } finally {
      setFeatureLoading(false)
    }
  }

  const handleDeadCode = async () => {
    setDeadCodeLoading(true)
    try {
      const data = await apiFetch('/api/dead-code')
      setDeadCode(data)
    } catch (e) {
      setDeadCode({ error: e.message })
    } finally {
      setDeadCodeLoading(false)
    }
  }

  return (
    <div className="analysis-tab">
      <div className="entity-input">
        <Autocomplete
          value={entityName}
          onChange={setEntityName}
          placeholder="Enter entity name (e.g., NASTRN, SDR2A, DPSE4)"
        />
      </div>

      <div className="feature-buttons">
        <button onClick={() => handleFeature('explain')} disabled={featureLoading}>Explain Code</button>
        <button onClick={() => handleFeature('dependencies')} disabled={featureLoading}>Map Dependencies</button>
        <button onClick={() => handleFeature('patterns')} disabled={featureLoading}>Find Patterns</button>
        <button onClick={() => handleFeature('generate-docs')} disabled={featureLoading}>Generate Docs</button>
        <button onClick={() => handleFeature('business-rules')} disabled={featureLoading}>Extract Rules</button>
      </div>

      <div className="feature-buttons" style={{ marginBottom: 12 }}>
        <button onClick={handleDeadCode} disabled={deadCodeLoading} className="dead-code-btn">
          {deadCodeLoading ? 'Scanning...' : 'Detect Dead Code'}
        </button>
      </div>

      {featureLoading && <div className="loading">Analyzing...</div>}

      {featureResult && !featureLoading && (
        <div className="feature-result">
          {featureResult.error ? (
            <div className="error-msg">Error: {featureResult.error}</div>
          ) : (
            <>
              {activeFeature === 'explain' && featureResult.explanation && (
                <div className="result-block">
                  <h3>Explanation: {featureResult.name}</h3>
                  <MarkdownContent text={featureResult.explanation} />
                </div>
              )}

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

              {activeFeature === 'generate-docs' && featureResult.documentation && (
                <div className="result-block">
                  <h3>Documentation: {featureResult.name}</h3>
                  <MarkdownContent text={featureResult.documentation} />
                </div>
              )}

              {activeFeature === 'business-rules' && featureResult.rules && (
                <div className="result-block">
                  <h3>Business Rules: {featureResult.name}</h3>
                  <MarkdownContent text={featureResult.rules} />
                </div>
              )}

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
      {deadCode && !deadCode.error && (
        <div className="result-block dead-code-results">
          <h3>Dead Code Analysis</h3>
          <div className="dead-code-stats">
            <span className="stat-pill">Total: {deadCode.stats.total_routines}</span>
            <span className="stat-pill">Callable: {deadCode.stats.callable_routines}</span>
            <span className="stat-pill dead">Dead: {deadCode.stats.dead_count}</span>
            <span className="stat-pill alive">Reachable: {deadCode.stats.reachable_count}</span>
            <span className="stat-pill">Coverage: {deadCode.stats.coverage_pct}%</span>
          </div>
          <p className="muted" style={{ marginBottom: 12 }}>{deadCode.disclaimer}</p>
          <div className="dead-code-table-wrap">
            <table className="dead-code-table">
              <thead><tr><th>Name</th><th>Type</th><th>File</th><th>Lines</th></tr></thead>
              <tbody>
                {deadCode.dead_routines.slice(0, 50).map((r, i) => (
                  <tr key={i}>
                    <td className="dc-name">{r.name}</td>
                    <td><span className="source-type">{r.chunk_type}</span></td>
                    <td className="source-path">{r.file_path}</td>
                    <td>{r.start_line}-{r.end_line}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {deadCode.dead_routines.length > 50 && (
              <p className="muted">Showing 50 of {deadCode.dead_routines.length} dead routines</p>
            )}
          </div>
        </div>
      )}

      {deadCode?.error && <div className="error-msg">Error: {deadCode.error}</div>}

      <div className="analysis-divider" />
      <XrefPanel />
    </div>
  )
}
