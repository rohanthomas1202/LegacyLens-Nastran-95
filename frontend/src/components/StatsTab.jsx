import { useState, useEffect } from 'react'
import { apiFetch } from '../api'
import AnimatedSparkline from './AnimatedSparkline'

export default function StatsTab() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    apiFetch('/api/stats').then(setStats).catch((e) => setStats({ error: e.message }))
  }, [])

  if (!stats) return <div className="loading">Initializing dashboard...</div>
  if (stats.error) return <div className="error-msg">Error: {stats.error}</div>

  return (
    <div className="stats-tab">
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Index</h3>
          <div className="stat-value">{stats.index?.total_vectors?.toLocaleString()}</div>
          <div className="stat-label">Total Vectors</div>
          <div className="stat-detail">{stats.index?.dimension}d embeddings</div>
        </div>

        <div className="stat-card">
          <h3>Queries</h3>
          <div className="stat-value">{stats.costs?.query_count}</div>
          <div className="stat-label">Total Queries</div>
          <div className="stat-detail">{stats.costs?.ingestion_count} ingestions</div>
        </div>

        <div className="stat-card">
          <h3>Total Cost</h3>
          <div className="stat-value">${stats.costs?.total_cost?.toFixed(4)}</div>
          <div className="stat-label">All API Costs</div>
        </div>

        <div className="stat-card">
          <h3>Activity</h3>
          <AnimatedSparkline width={200} height={60} />
          <div className="stat-label">Query Velocity</div>
        </div>
      </div>

      <div className="cost-breakdown">
        <h3>Cost Breakdown</h3>
        <table>
          <thead><tr><th>Category</th><th>Tokens</th><th>Cost</th></tr></thead>
          <tbody>
            <tr>
              <td>Embeddings</td>
              <td>{stats.costs?.embedding_tokens?.toLocaleString()}</td>
              <td>${stats.costs?.embedding_cost?.toFixed(4)}</td>
            </tr>
            <tr>
              <td>LLM Input</td>
              <td>{stats.costs?.llm_input_tokens?.toLocaleString()}</td>
              <td>${stats.costs?.llm_input_cost?.toFixed(4)}</td>
            </tr>
            <tr>
              <td>LLM Output</td>
              <td>{stats.costs?.llm_output_tokens?.toLocaleString()}</td>
              <td>${stats.costs?.llm_output_cost?.toFixed(4)}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr><td><strong>Total</strong></td><td></td><td><strong>${stats.costs?.total_cost?.toFixed(4)}</strong></td></tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}
