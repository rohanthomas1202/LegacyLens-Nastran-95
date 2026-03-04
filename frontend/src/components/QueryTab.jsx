import { useState } from 'react'
import { API_BASE } from '../api'
import SourceCard from './SourceCard'
import MarkdownContent from './MarkdownContent'

const SAMPLE_QUERIES = [
  'Where is the main entry point of this program?',
  'What functions handle stiffness matrix assembly?',
  'Explain the GINO I/O system',
  'Find all error handling patterns',
  'What are the dependencies of the NASTRN module?',
]

export default function QueryTab({ onViewFile }) {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState(null)
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedSource, setExpandedSource] = useState(null)
  const [streaming, setStreaming] = useState(false)

  const handleQuery = async (q) => {
    const queryText = q || query
    if (!queryText.trim()) return
    setLoading(true)
    setStreaming(true)
    setError(null)
    setAnswer('')
    setSources([])

    try {
      const res = await fetch(`${API_BASE}/api/query/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText, top_k: 5 }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullAnswer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() // keep incomplete line

        let eventType = null
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7)
          } else if (line.startsWith('data: ') && eventType) {
            const data = line.slice(6)
            try {
              const parsed = JSON.parse(data)
              if (eventType === 'sources') {
                setSources(parsed)
                setLoading(false)
              } else if (eventType === 'token') {
                fullAnswer += parsed
                setAnswer(fullAnswer)
              } else if (eventType === 'done') {
                setStreaming(false)
              }
            } catch { /* skip malformed */ }
            eventType = null
          }
        }
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
      setStreaming(false)
    }
  }

  return (
    <div className="query-tab">
      <div className="query-input">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question about the NASTRAN-95 codebase..."
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleQuery() } }}
        />
        <button onClick={() => handleQuery()} disabled={loading || streaming}>
          {loading ? 'Searching...' : streaming ? 'Streaming...' : 'Search'}
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
          <h3>Answer {streaming && <span className="timing streaming-indicator">streaming...</span>}</h3>
          <MarkdownContent text={answer} />
        </div>
      )}

      {sources.length > 0 && (
        <div className="sources-section">
          <h3>Sources ({sources.length})</h3>
          {sources.map((source, i) => (
            <SourceCard
              key={i}
              source={source}
              index={i}
              isExpanded={expandedSource === i}
              onToggle={() => setExpandedSource(expandedSource === i ? null : i)}
              onViewFile={onViewFile}
            />
          ))}
        </div>
      )}
    </div>
  )
}
