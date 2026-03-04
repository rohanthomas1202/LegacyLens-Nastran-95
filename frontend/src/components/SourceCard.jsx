import { Light as SyntaxHighlighter } from 'react-syntax-highlighter'
import fortran from 'react-syntax-highlighter/dist/esm/languages/hljs/fortran'
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs'

SyntaxHighlighter.registerLanguage('fortran', fortran)

const codeStyle = {
  ...atomOneDark,
  'hljs': {
    ...atomOneDark['hljs'],
    background: 'rgba(5, 5, 5, 0.6)',
  },
  'hljs-keyword': { color: '#ff00e5' },
  'hljs-string': { color: '#adff00' },
  'hljs-number': { color: '#00f2ff' },
  'hljs-built_in': { color: '#00f2ff' },
  'hljs-comment': { color: '#555', fontStyle: 'italic' },
}

export default function SourceCard({ source, index, isExpanded, onToggle, onViewFile }) {
  return (
    <div className="source-card">
      <div className="source-header" onClick={onToggle}>
        <div className="source-info">
          <span className="source-name">{source.name}</span>
          <span className="source-type">{source.chunk_type}</span>
          <span className="source-path">{source.file_path}:{source.start_line}-{source.end_line}</span>
        </div>
        <div className="source-actions">
          <span className="score-badge">{(source.score * 100).toFixed(0)}%</span>
          <button
            className="view-file-btn"
            onClick={(e) => { e.stopPropagation(); onViewFile(source.file_path, source.start_line) }}
          >
            View File
          </button>
          <span className="expand-icon">{isExpanded ? '▾' : '▸'}</span>
        </div>
      </div>
      {isExpanded && (
        <SyntaxHighlighter
          language="fortran"
          style={codeStyle}
          showLineNumbers={true}
          startingLineNumber={source.start_line || 1}
          customStyle={{
            margin: 0,
            borderRadius: 0,
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            fontSize: '0.82rem',
            fontFamily: "'Space Grotesk', monospace",
          }}
        >
          {source.content || '// No content available'}
        </SyntaxHighlighter>
      )}
    </div>
  )
}
