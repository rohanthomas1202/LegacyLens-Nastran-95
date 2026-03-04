import { useState } from 'react'
import CommonBlocksPanel from './CommonBlocksPanel'
import ComplexityPanel from './ComplexityPanel'

const SUB_TABS = [
  { key: 'common', label: 'COMMON Blocks' },
  { key: 'complexity', label: 'Complexity Metrics' },
]

export default function InsightsTab() {
  const [sub, setSub] = useState('common')

  return (
    <div className="insights-tab">
      <div className="insights-nav">
        {SUB_TABS.map(t => (
          <button
            key={t.key}
            className={`insights-nav-btn ${sub === t.key ? 'active' : ''}`}
            onClick={() => setSub(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ display: sub === 'common' ? 'block' : 'none' }}>
        <CommonBlocksPanel />
      </div>

      <div style={{ display: sub === 'complexity' ? 'block' : 'none' }}>
        <ComplexityPanel />
      </div>
    </div>
  )
}
