export default function MarkdownContent({ text }) {
  if (!text) return null
  return (
    <div className="markdown-content">
      {text.split('\n').map((line, i) => {
        if (line.startsWith('### ')) return <h5 key={i}>{line.replace('### ', '')}</h5>
        if (line.startsWith('## ')) return <h4 key={i}>{line.replace('## ', '')}</h4>
        if (line.startsWith('**') && line.endsWith('**')) return <strong key={i}>{line.replace(/\*\*/g, '')}<br/></strong>
        if (line.startsWith('- **')) return <li key={i} dangerouslySetInnerHTML={{ __html: line.replace('- ', '').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
        if (line.startsWith('- ')) return <li key={i}>{line.replace('- ', '')}</li>
        if (line.trim() === '') return <br key={i} />
        return <p key={i}>{line}</p>
      })}
    </div>
  )
}
