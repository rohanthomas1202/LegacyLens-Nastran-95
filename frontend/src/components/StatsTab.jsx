import { useState, useEffect, useRef } from 'react'
import { apiFetch } from '../api'

const MODE_COLORS = {
  query: '#00f2ff',
  explain: '#22c55e',
  patterns: '#f59e0b',
  docgen: '#a855f7',
  translate: '#ef4444',
  dependencies: '#3b82f6',
  'business-rules': '#ec4899',
  search: '#6366f1',
}

function formatTokens(n) {
  if (!n) return '0'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return n.toString()
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) +
    ', ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

function LatencyChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="chart-empty">No latency data yet</div>
  }

  const W = 500, H = 180, PAD_L = 50, PAD_B = 30, PAD_T = 10, PAD_R = 10
  const plotW = W - PAD_L - PAD_R
  const plotH = H - PAD_T - PAD_B

  const maxLatency = Math.max(...data.map(d => d.latency), 1000)
  const yMax = Math.ceil(maxLatency / 1000) * 1000

  const points = data.map((d, i) => {
    const x = PAD_L + (i / Math.max(data.length - 1, 1)) * plotW
    const y = PAD_T + plotH - (d.latency / yMax) * plotH
    return { x, y }
  })

  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')

  const areaD = pathD
    + ` L ${points[points.length - 1].x.toFixed(1)} ${(PAD_T + plotH).toFixed(1)}`
    + ` L ${points[0].x.toFixed(1)} ${(PAD_T + plotH).toFixed(1)} Z`

  const yTicks = 5
  const gridLines = Array.from({ length: yTicks + 1 }, (_, i) => {
    const val = (yMax / yTicks) * i
    const y = PAD_T + plotH - (val / yMax) * plotH
    return { val, y }
  })

  const tickCount = Math.min(data.length, 6)
  const xTicks = Array.from({ length: tickCount }, (_, i) => {
    const idx = Math.round((i / Math.max(tickCount - 1, 1)) * (data.length - 1))
    const x = PAD_L + (idx / Math.max(data.length - 1, 1)) * plotW
    return { x, label: formatTime(data[idx]?.time) }
  })

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="dash-chart-svg">
      <defs>
        <linearGradient id="latency-gradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#00f2ff" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#00f2ff" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="latency-stroke" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#00f2ff" />
          <stop offset="100%" stopColor="#a855f7" />
        </linearGradient>
      </defs>

      {gridLines.map((g, i) => (
        <g key={i}>
          <line x1={PAD_L} y1={g.y} x2={W - PAD_R} y2={g.y} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
          <text x={PAD_L - 8} y={g.y + 4} textAnchor="end" className="dash-chart-label">{g.val}ms</text>
        </g>
      ))}

      {xTicks.map((t, i) => (
        <text key={i} x={t.x} y={H - 4} textAnchor="middle" className="dash-chart-label">{t.label}</text>
      ))}

      <path d={areaD} fill="url(#latency-gradient)" />
      <path d={pathD} fill="none" stroke="url(#latency-stroke)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="3" fill="#050505" stroke="#00f2ff" strokeWidth="1.5" opacity="0.7" />
      ))}
    </svg>
  )
}

function DonutChart({ data }) {
  if (!data || Object.keys(data).length === 0) {
    return <div className="chart-empty">No usage data yet</div>
  }

  const total = Object.values(data).reduce((a, b) => a + b, 0)
  if (total === 0) return <div className="chart-empty">No usage data yet</div>

  const R = 70, r = 45, CX = 90, CY = 90
  const circumference = 2 * Math.PI * R

  let offset = 0
  const slices = Object.entries(data).map(([mode, count]) => {
    const pct = count / total
    const dashLength = pct * circumference
    const slice = { mode, count, pct, dashLength, offset, color: MODE_COLORS[mode] || '#666' }
    offset += dashLength
    return slice
  })

  return (
    <div className="donut-wrapper">
      <svg viewBox="0 0 180 180" className="donut-svg">
        {slices.map((s, i) => (
          <circle
            key={i}
            cx={CX} cy={CY} r={R}
            fill="none"
            stroke={s.color}
            strokeWidth={R - r}
            strokeDasharray={`${s.dashLength} ${circumference - s.dashLength}`}
            strokeDashoffset={-s.offset}
            transform={`rotate(-90 ${CX} ${CY})`}
          />
        ))}
        <text x={CX} y={CY - 6} textAnchor="middle" className="donut-total">{total}</text>
        <text x={CX} y={CY + 12} textAnchor="middle" className="donut-total-label">queries</text>
      </svg>
      <div className="donut-legend">
        {slices.map((s, i) => (
          <div key={i} className="donut-legend-item">
            <span className="donut-legend-dot" style={{ background: s.color }} />
            <span className="donut-legend-name">{s.mode}</span>
            <span className="donut-legend-count">{s.count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ScoreDistribution({ data }) {
  if (!data) return null

  const entries = Object.entries(data)
  const maxVal = Math.max(...entries.map(([, v]) => v), 1)

  return (
    <div className="score-dist">
      {entries.map(([range, count]) => (
        <div key={range} className="score-dist-bar-group">
          <div className="score-dist-bar-track">
            <div
              className="score-dist-bar-fill"
              style={{ height: `${(count / maxVal) * 100}%` }}
            />
          </div>
          <span className="score-dist-count">{count}</span>
          <span className="score-dist-label">{range}</span>
        </div>
      ))}
    </div>
  )
}

function ModeBadge({ mode }) {
  const color = MODE_COLORS[mode] || '#666'
  return (
    <span className="mode-badge" style={{ color, borderColor: color, background: `${color}15` }}>
      {mode}
    </span>
  )
}

export default function StatsTab() {
  const [stats, setStats] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const intervalRef = useRef(null)

  const fetchStats = () => {
    apiFetch('/api/stats').then(setStats).catch((e) => setStats({ error: e.message }))
  }

  useEffect(() => {
    fetchStats()
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchStats, 30000)
    }
    return () => clearInterval(intervalRef.current)
  }, [autoRefresh])

  if (!stats) return <div className="loading">Initializing dashboard...</div>
  if (stats.error) return <div className="error-msg">Error: {stats.error}</div>

  const d = stats.dashboard || {}
  const c = stats.costs || {}
  const idx = stats.index || {}

  return (
    <div className="dashboard">
      {/* ── Top KPI Row ── */}
      <div className="dash-kpi-grid">
        <div className="dash-kpi" data-accent="cyan">
          <span className="dash-kpi-label">Total Queries</span>
          <span className="dash-kpi-value">{c.query_count ?? 0}</span>
        </div>
        <div className="dash-kpi" data-accent="magenta">
          <span className="dash-kpi-label">Avg Latency</span>
          <span className="dash-kpi-value">{d.avg_latency ?? 0}<small>ms</small></span>
        </div>
        <div className="dash-kpi" data-accent="lime">
          <span className="dash-kpi-label">API Cost</span>
          <span className="dash-kpi-value">${c.total_cost?.toFixed(4) ?? '0.00'}</span>
        </div>
        <div className="dash-kpi" data-accent="purple">
          <span className="dash-kpi-label">Avg Score</span>
          <span className="dash-kpi-value">{d.avg_score ?? 0}<small>%</small></span>
        </div>
        <div className="dash-kpi" data-accent="blue">
          <span className="dash-kpi-label">Chunks Indexed</span>
          <span className="dash-kpi-value">{(idx.total_vectors ?? 0).toLocaleString()}</span>
        </div>
        <div className="dash-kpi" data-accent="white">
          <span className="dash-kpi-label">Files Covered</span>
          <span className="dash-kpi-value">{(d.files_covered ?? 0).toLocaleString()}</span>
        </div>
      </div>

      {/* ── Secondary KPI Row ── */}
      <div className="dash-kpi-row-2">
        <div className="dash-kpi" data-accent="cyan">
          <span className="dash-kpi-label">Total Tokens</span>
          <span className="dash-kpi-value">{formatTokens(d.total_tokens)}</span>
        </div>
        <div className="dash-kpi" data-accent="lime">
          <span className="dash-kpi-label">Satisfaction</span>
          <span className="dash-kpi-value">{d.satisfaction ?? 100}<small>%</small></span>
        </div>
        <div className="dash-kpi" data-accent="magenta">
          <span className="dash-kpi-label">Ingestions</span>
          <span className="dash-kpi-value">{c.ingestion_count ?? 0}</span>
        </div>
        <div className="dash-kpi-refresh">
          <button
            className={`feature-btn-sm ${autoRefresh ? 'active-toggle' : ''}`}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}
          </button>
          <button className="feature-btn-sm" onClick={fetchStats}>Refresh Now</button>
        </div>
      </div>

      {/* ── Charts Row ── */}
      <div className="dash-charts-row">
        <div className="dash-chart-card">
          <h3>Latency Over Time</h3>
          <LatencyChart data={d.latency_series} />
        </div>
        <div className="dash-chart-card">
          <h3>Usage by Mode</h3>
          <DonutChart data={d.usage_by_mode} />
        </div>
      </div>

      {/* ── Score Distribution ── */}
      <div className="dash-chart-card dash-full-width">
        <h3>Retrieval Score Distribution</h3>
        <ScoreDistribution data={d.score_distribution} />
      </div>

      {/* ── Cost Breakdown ── */}
      <div className="cost-breakdown">
        <h3>Cost Breakdown</h3>
        <table>
          <thead><tr><th>Category</th><th>Tokens</th><th>Cost</th></tr></thead>
          <tbody>
            <tr>
              <td>Embeddings</td>
              <td>{c.embedding_tokens?.toLocaleString()}</td>
              <td>${c.embedding_cost?.toFixed(4)}</td>
            </tr>
            <tr>
              <td>LLM Input</td>
              <td>{c.llm_input_tokens?.toLocaleString()}</td>
              <td>${c.llm_input_cost?.toFixed(4)}</td>
            </tr>
            <tr>
              <td>LLM Output</td>
              <td>{c.llm_output_tokens?.toLocaleString()}</td>
              <td>${c.llm_output_cost?.toFixed(4)}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr><td><strong>Total</strong></td><td></td><td><strong>${c.total_cost?.toFixed(4)}</strong></td></tr>
          </tfoot>
        </table>
      </div>

      {/* ── Recent Queries Table ── */}
      <div className="dash-recent">
        <h3>Recent Queries</h3>
        {(!d.recent_queries || d.recent_queries.length === 0) ? (
          <p className="muted">No queries recorded yet. Start querying to see history here.</p>
        ) : (
          <div className="dash-table-wrap">
            <table className="dash-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Query</th>
                  <th>Mode</th>
                  <th>Latency</th>
                  <th>Cost</th>
                  <th>Top Score</th>
                  <th>Chunks</th>
                </tr>
              </thead>
              <tbody>
                {d.recent_queries.map((q, i) => (
                  <tr key={i}>
                    <td className="dash-cell-time">{formatTime(q.timestamp)}</td>
                    <td className="dash-cell-query">{q.query}</td>
                    <td><ModeBadge mode={q.mode} /></td>
                    <td>{q.latency_ms}ms</td>
                    <td>${q.cost?.toFixed(4)}</td>
                    <td>{Math.round(q.top_score * 100)}%</td>
                    <td>{q.chunks}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
