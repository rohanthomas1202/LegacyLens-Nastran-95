import { useState, useEffect } from 'react'
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

const HISTORY_KEY = 'codex95_query_history'
const BOOKMARKS_KEY = 'codex95_bookmarks'
const MAX_HISTORY = 50

function loadFromStorage(key, fallback = []) {
  try { return JSON.parse(localStorage.getItem(key)) || fallback } catch { return fallback }
}

export default function QueryTab({ onViewFile }) {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState(null)
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedSource, setExpandedSource] = useState(null)
  const [streaming, setStreaming] = useState(false)
  const [history, setHistory] = useState(() => loadFromStorage(HISTORY_KEY))
  const [bookmarks, setBookmarks] = useState(() => loadFromStorage(BOOKMARKS_KEY))
  const [showHistory, setShowHistory] = useState(false)
  const [showBookmarks, setShowBookmarks] = useState(false)

  useEffect(() => { localStorage.setItem(HISTORY_KEY, JSON.stringify(history)) }, [history])
  useEffect(() => { localStorage.setItem(BOOKMARKS_KEY, JSON.stringify(bookmarks)) }, [bookmarks])

  const addToHistory = (q) => {
    setHistory(prev => {
      const filtered = prev.filter(h => h.query !== q)
      return [{ query: q, timestamp: Date.now() }, ...filtered].slice(0, MAX_HISTORY)
    })
  }

  const toggleBookmark = () => {
    if (!query.trim() || !answer) return
    const existing = bookmarks.find(b => b.query === query)
    if (existing) {
      setBookmarks(prev => prev.filter(b => b.query !== query))
    } else {
      setBookmarks(prev => [{ query, answer: answer?.slice(0, 500), timestamp: Date.now() }, ...prev])
    }
  }

  const isBookmarked = bookmarks.some(b => b.query === query)

  const handleQuery = async (q) => {
    const queryText = q || query
    if (!queryText.trim()) return
    addToHistory(queryText)
    setShowHistory(false)
    setShowBookmarks(false)
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

      <div className="query-toolbar">
        <div className="sample-queries">
          {SAMPLE_QUERIES.map((q, i) => (
            <button key={i} onClick={() => { setQuery(q); handleQuery(q) }} className="sample-btn">{q}</button>
          ))}
        </div>
        <div className="history-buttons">
          <button onClick={() => { setShowHistory(!showHistory); setShowBookmarks(false) }}
            className={`history-btn ${showHistory ? 'active' : ''}`}>
            History ({history.length})
          </button>
          <button onClick={() => { setShowBookmarks(!showBookmarks); setShowHistory(false) }}
            className={`history-btn ${showBookmarks ? 'active' : ''}`}>
            Bookmarks ({bookmarks.length})
          </button>
        </div>
      </div>

      {showHistory && history.length > 0 && (
        <div className="history-panel">
          <div className="history-header">
            <span>Recent Queries</span>
            <button onClick={() => { setHistory([]); setShowHistory(false) }} className="history-clear">Clear</button>
          </div>
          {history.map((h, i) => (
            <div key={i} className="history-item" onClick={() => { setQuery(h.query); handleQuery(h.query) }}>
              <span>{h.query}</span>
              <span className="source-path">{new Date(h.timestamp).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}

      {showBookmarks && bookmarks.length > 0 && (
        <div className="history-panel">
          <div className="history-header">
            <span>Bookmarked Queries</span>
          </div>
          {bookmarks.map((b, i) => (
            <div key={i} className="history-item">
              <div style={{ flex: 1, cursor: 'pointer' }} onClick={() => { setQuery(b.query); handleQuery(b.query) }}>
                <div>{b.query}</div>
                {b.answer && <div className="source-path" style={{ marginTop: 4 }}>{b.answer.slice(0, 100)}...</div>}
              </div>
              <button onClick={() => setBookmarks(prev => prev.filter((_, j) => j !== i))}
                className="history-clear" style={{ fontSize: '0.7rem' }}>Remove</button>
            </div>
          ))}
        </div>
      )}

      {error && <div className="error-msg">Error: {error}</div>}

      {answer && (
        <div className="answer-section">
          <h3>
            Answer
            {streaming && <span className="timing streaming-indicator">streaming...</span>}
            {!streaming && answer && (
              <button onClick={toggleBookmark} className={`bookmark-btn ${isBookmarked ? 'bookmarked' : ''}`}>
                {isBookmarked ? '★' : '☆'}
              </button>
            )}
          </h3>
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
