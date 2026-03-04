import { useState, lazy, Suspense } from 'react'
import { apiPost } from './api'
import QueryTab from './components/QueryTab'
import AnalysisTab from './components/AnalysisTab'
import StatsTab from './components/StatsTab'
import FileModal from './components/FileModal'
import NeonStatusIndicator from './components/NeonStatusIndicator'
import CursorGlow from './components/CursorGlow'
import './App.css'

const DependencyGraph = lazy(() => import('./components/DependencyGraph'))
const CodeFlowTracer = lazy(() => import('./components/CodeFlowTracer'))

export default function App() {
  const [tab, setTab] = useState('query')
  const [fullFile, setFullFile] = useState(null)

  const loadFullFile = async (filePath, startLine) => {
    try {
      const data = await apiPost('/api/file', { file_path: filePath })
      setFullFile({ ...data, highlightStart: startLine })
    } catch (e) {
      alert(`Could not load file: ${e.message}`)
    }
  }

  return (
    <>
      <CursorGlow />
      <nav className="nav-header">
        <div className="nav-logo">
          <div className="nav-logo-icon">&#9741;</div>
          <span className="nav-logo-text">CODEX-95</span>
        </div>

        <div className="nav-links">
          <button className={tab === 'query' ? 'active' : ''} onClick={() => setTab('query')}>Query</button>
          <button className={tab === 'analysis' ? 'active' : ''} onClick={() => setTab('analysis')}>Analysis</button>
          <button className={tab === 'graph' ? 'active' : ''} onClick={() => setTab('graph')}>Graph</button>
          <button className={tab === 'stats' ? 'active' : ''} onClick={() => setTab('stats')}>Dashboard</button>
        </div>

        <div className="nav-right">
          <NeonStatusIndicator />
          <button className="nav-console-btn" onClick={() => setTab('query')}>Console</button>
        </div>
      </nav>

      <div className={`app ${tab === 'graph' ? 'app-fullwidth' : ''}`}>
        <div className="hero-section">
          <h1 className="hero-title">
            <span className="accent">CODEX</span>-95
          </h1>
          <p className="hero-subtitle">
            AI-powered code intelligence for NASA NASTRAN-95. Query, analyze, and visualize legacy Fortran with natural language.
          </p>
        </div>

        <main className="content">
          {tab === 'query' && <QueryTab onViewFile={loadFullFile} />}
          {tab === 'analysis' && <AnalysisTab />}
          {tab === 'graph' && (
            <Suspense fallback={<div className="loading">Initializing graph engine...</div>}>
              <DependencyGraph />
              <CodeFlowTracer onSwitchToGraph={(name) => setTab('graph')} />
            </Suspense>
          )}
          {tab === 'stats' && <StatsTab />}
        </main>
      </div>

      <FileModal fullFile={fullFile} onClose={() => setFullFile(null)} />
    </>
  )
}
