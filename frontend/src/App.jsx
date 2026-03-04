import { useState, lazy, Suspense } from 'react'
import { apiPost } from './api'
import QueryTab from './components/QueryTab'
import AnalysisTab from './components/AnalysisTab'
import ModernizeTab from './components/ModernizeTab'
import InsightsTab from './components/InsightsTab'
import StatsTab from './components/StatsTab'
import FileModal from './components/FileModal'
import NeonStatusIndicator from './components/NeonStatusIndicator'
import CursorGlow from './components/CursorGlow'
import './App.css'

const DependencyGraph = lazy(() => import('./components/DependencyGraph'))
const CodeFlowTracer = lazy(() => import('./components/CodeFlowTracer'))
const ImpactPanel = lazy(() => import('./components/ImpactPanel'))
const CallSimulator = lazy(() => import('./components/CallSimulator'))

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
          <button className={tab === 'modernize' ? 'active' : ''} onClick={() => setTab('modernize')}>Modernize</button>
          <button className={tab === 'graph' ? 'active' : ''} onClick={() => setTab('graph')}>Graph</button>
          <button className={tab === 'insights' ? 'active' : ''} onClick={() => setTab('insights')}>Insights</button>
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
          {tab === 'modernize' && <ModernizeTab />}
          {tab === 'graph' && (
            <Suspense fallback={<div className="loading">Initializing graph engine...</div>}>
              <DependencyGraph />
              <div className="analysis-divider" />
              <CodeFlowTracer onSwitchToGraph={(name) => setTab('graph')} />
              <div className="analysis-divider" />
              <ImpactPanel />
              <div className="analysis-divider" />
              <CallSimulator />
            </Suspense>
          )}
          {tab === 'insights' && <InsightsTab />}
          {tab === 'stats' && <StatsTab />}
        </main>
      </div>

      <FileModal fullFile={fullFile} onClose={() => setFullFile(null)} />
    </>
  )
}
