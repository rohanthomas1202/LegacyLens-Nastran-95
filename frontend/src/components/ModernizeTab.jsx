import { useState } from 'react'
import { apiPost } from '../api'
import Autocomplete from './Autocomplete'
import ModernizeModal from './ModernizeModal'
import BatchModernizePanel from './BatchModernizePanel'

const EXAMPLES = [
  { name: 'NASTRN', desc: 'Main NASTRAN driver program', lang: 'python' },
  { name: 'SDR2A', desc: 'Stress data recovery', lang: 'python' },
  { name: 'XSORT', desc: 'Sort utility routine', lang: 'python' },
  { name: 'GFSWT', desc: 'Grid point force balance', lang: 'c' },
  { name: 'DPSE4', desc: 'Dynamic element processing', lang: 'rust' },
  { name: 'RBMG1', desc: 'Rigid body matrix generation', lang: 'java' },
]

export default function ModernizeTab() {
  const [entityName, setEntityName] = useState('')
  const [targetLanguage, setTargetLanguage] = useState('python')
  const [modernizeResult, setModernizeResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleModernize = async (name, lang) => {
    const routineName = name || entityName
    const routineLang = lang || targetLanguage
    if (!routineName.trim()) return
    setEntityName(routineName)
    setTargetLanguage(routineLang)
    setLoading(true)
    setError(null)
    setModernizeResult(null)

    try {
      const data = await apiPost('/api/modernize', {
        name: routineName,
        target_language: routineLang,
      })
      if (data.error) {
        setError(data.error)
      } else {
        setModernizeResult(data)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modernize-tab">
      <div className="result-block">
        <h3>Single Routine</h3>
        <p className="muted">Translate a Fortran 77 routine to a modern language</p>

        <div className="flow-inputs" style={{ marginBottom: 16 }}>
          <div className="flow-field" style={{ flex: 1 }}>
            <Autocomplete value={entityName} onChange={setEntityName} placeholder="Routine name..." />
          </div>
          <select
            className="language-select"
            value={targetLanguage}
            onChange={(e) => setTargetLanguage(e.target.value)}
            disabled={loading}
          >
            <option value="python">Python</option>
            <option value="c">C</option>
            <option value="java">Java</option>
            <option value="rust">Rust</option>
          </select>
          <button onClick={() => handleModernize()} disabled={loading} className="flow-btn">
            {loading ? 'Translating...' : 'Modernize'}
          </button>
        </div>

        <div className="modernize-examples">
          <h4>Try an example</h4>
          <div className="example-chips">
            {EXAMPLES.map(ex => (
              <button
                key={ex.name}
                className="example-chip"
                onClick={() => handleModernize(ex.name, ex.lang)}
                disabled={loading}
              >
                <span className="example-chip-name">{ex.name}</span>
                <span className="example-chip-desc">{ex.desc}</span>
                <span className="example-chip-lang">{ex.lang}</span>
              </button>
            ))}
          </div>
        </div>

        {error && <div className="error-msg" style={{ marginTop: 12 }}>Error: {error}</div>}
      </div>

      <div className="analysis-divider" />

      <BatchModernizePanel />

      <ModernizeModal
        result={modernizeResult}
        onClose={() => setModernizeResult(null)}
      />
    </div>
  )
}
