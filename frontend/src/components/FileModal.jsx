import { Light as SyntaxHighlighter } from 'react-syntax-highlighter'
import fortran from 'react-syntax-highlighter/dist/esm/languages/hljs/fortran'
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs'

SyntaxHighlighter.registerLanguage('fortran', fortran)

const codeStyle = {
  ...atomOneDark,
  'hljs': {
    ...atomOneDark['hljs'],
    background: '#050505',
  },
  'hljs-keyword': { color: '#ff00e5' },
  'hljs-string': { color: '#adff00' },
  'hljs-number': { color: '#00f2ff' },
  'hljs-built_in': { color: '#00f2ff' },
  'hljs-comment': { color: '#555', fontStyle: 'italic' },
}

export default function FileModal({ fullFile, onClose }) {
  if (!fullFile) return null
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-dots">
            <span className="modal-dot red" />
            <span className="modal-dot yellow" />
            <span className="modal-dot green" />
          </div>
          <span className="modal-title">{fullFile.file_path}</span>
          <span className="modal-lines">{fullFile.total_lines} lines</span>
          <button className="modal-close" onClick={onClose}>Close</button>
        </div>
        <div className="modal-body">
          <SyntaxHighlighter
            language="fortran"
            style={codeStyle}
            showLineNumbers={true}
            wrapLines={true}
            lineProps={(lineNumber) => {
              const hl = fullFile.highlightStart
              if (hl && lineNumber >= hl && lineNumber <= hl + 30) {
                return { style: { backgroundColor: 'rgba(0, 242, 255, 0.06)' } }
              }
              return {}
            }}
            customStyle={{ margin: 0, fontSize: '0.85rem', background: '#050505', fontFamily: "'Space Grotesk', monospace" }}
          >
            {fullFile.content}
          </SyntaxHighlighter>
        </div>
      </div>
    </div>
  )
}
