import { Light as SyntaxHighlighter } from 'react-syntax-highlighter'
import fortran from 'react-syntax-highlighter/dist/esm/languages/hljs/fortran'
import python from 'react-syntax-highlighter/dist/esm/languages/hljs/python'
import c from 'react-syntax-highlighter/dist/esm/languages/hljs/c'
import java from 'react-syntax-highlighter/dist/esm/languages/hljs/java'
import rust from 'react-syntax-highlighter/dist/esm/languages/hljs/rust'
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs'
import MarkdownContent from './MarkdownContent'

SyntaxHighlighter.registerLanguage('fortran', fortran)
SyntaxHighlighter.registerLanguage('python', python)
SyntaxHighlighter.registerLanguage('c', c)
SyntaxHighlighter.registerLanguage('java', java)
SyntaxHighlighter.registerLanguage('rust', rust)

const codeStyle = {
  ...atomOneDark,
  'hljs': { ...atomOneDark['hljs'], background: '#050505' },
  'hljs-keyword': { color: '#ff00e5' },
  'hljs-string': { color: '#adff00' },
  'hljs-number': { color: '#00f2ff' },
  'hljs-built_in': { color: '#00f2ff' },
  'hljs-comment': { color: '#555', fontStyle: 'italic' },
}

const LANGUAGE_LABELS = {
  python: 'Python',
  c: 'C',
  java: 'Java',
  rust: 'Rust',
}

export default function ModernizeModal({ result, onClose }) {
  if (!result) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modernize-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-dots">
            <span className="modal-dot red" />
            <span className="modal-dot yellow" />
            <span className="modal-dot green" />
          </div>
          <span className="modal-title">
            {result.name} — Fortran 77 → {LANGUAGE_LABELS[result.target_language]}
          </span>
          <button className="modal-close" onClick={onClose}>Close</button>
        </div>

        <div className="modernize-body">
          <div className="modernize-panes">
            <div className="modernize-pane">
              <div className="pane-header">
                <span className="pane-label">Fortran 77</span>
                <span className="pane-tag original">Original</span>
              </div>
              <SyntaxHighlighter
                language="fortran"
                style={codeStyle}
                showLineNumbers={true}
                customStyle={{
                  margin: 0,
                  fontSize: '0.82rem',
                  fontFamily: "'Space Grotesk', monospace",
                  background: '#050505',
                  minHeight: '300px',
                  flex: 1,
                }}
              >
                {result.original_code || '// No source available'}
              </SyntaxHighlighter>
            </div>

            <div className="modernize-pane">
              <div className="pane-header">
                <span className="pane-label">{LANGUAGE_LABELS[result.target_language]}</span>
                <span className="pane-tag translated">Translated</span>
              </div>
              <SyntaxHighlighter
                language={result.target_language}
                style={codeStyle}
                showLineNumbers={true}
                customStyle={{
                  margin: 0,
                  fontSize: '0.82rem',
                  fontFamily: "'Space Grotesk', monospace",
                  background: '#050505',
                  minHeight: '300px',
                  flex: 1,
                }}
              >
                {result.translated_code || '// Translation not available'}
              </SyntaxHighlighter>
            </div>
          </div>

          {result.migration_notes && (
            <div className="modernize-notes">
              <h3>Migration Notes</h3>
              <MarkdownContent text={result.migration_notes} />
            </div>
          )}

          {result.sources?.length > 0 && (
            <div className="feature-sources" style={{ padding: '16px 24px' }}>
              <h4>Sources</h4>
              {result.sources.map((s, i) => (
                <span key={i} className="source-ref">
                  {s.name} — {s.file_path}:{s.start_line}-{s.end_line}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
