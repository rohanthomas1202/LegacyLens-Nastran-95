import { useState, useRef, useEffect, useCallback } from 'react'
import * as d3 from 'd3'
import { apiPost } from '../api'
import Autocomplete from './Autocomplete'

const TYPE_COLORS = {
  subroutine: '#4a9eff',
  function: '#50c878',
  program: '#ffd700',
  'block-data': '#ff6b6b',
  entry: '#c084fc',
  routine: '#888',
}

function Graph2D({ graphData, onNodeClick }) {
  const canvasRef = useRef(null)
  const tooltipRef = useRef(null)
  const simRef = useRef(null)
  const zoomRef = useRef(null)

  const fitToView = useCallback(() => {
    if (!simRef.current || !canvasRef.current || !zoomRef.current) return
    const canvas = canvasRef.current
    const nodes = simRef.current.nodes()
    if (nodes.length === 0) return

    const width = canvas.clientWidth
    const height = canvas.clientHeight

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    for (const n of nodes) {
      if (n.x < minX) minX = n.x
      if (n.y < minY) minY = n.y
      if (n.x > maxX) maxX = n.x
      if (n.y > maxY) maxY = n.y
    }

    const padding = 40
    const bw = maxX - minX || 1
    const bh = maxY - minY || 1
    const scale = Math.min((width - padding * 2) / bw, (height - padding * 2) / bh, 2)
    const cx = (minX + maxX) / 2
    const cy = (minY + maxY) / 2
    const tx = width / 2 - cx * scale
    const ty = height / 2 - cy * scale

    const newTransform = d3.zoomIdentity.translate(tx, ty).scale(scale)
    d3.select(canvas).transition().duration(300).call(zoomRef.current.transform, newTransform)
  }, [])

  useEffect(() => {
    if (!graphData || !canvasRef.current) return
    if (simRef.current) simRef.current.stop()

    const canvas = canvasRef.current
    const container = canvas.parentElement
    const rect = container.getBoundingClientRect()
    const width = rect.width || container.clientWidth
    const height = rect.height || container.clientHeight || 500
    const dpr = window.devicePixelRatio || 1
    canvas.width = width * dpr
    canvas.height = height * dpr
    canvas.style.width = width + 'px'
    canvas.style.height = height + 'px'
    const ctx = canvas.getContext('2d')
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    const edgeSet = new Set()
    const nodes = Object.entries(graphData.nodes).map(([name, info]) => ({
      id: name, ...info,
    }))
    const links = graphData.edges
      .filter(e => {
        const key = `${e.source}->${e.target}`
        if (edgeSet.has(key)) return false
        edgeSet.add(key)
        return graphData.nodes[e.source] && graphData.nodes[e.target]
      })
      .map(e => ({ source: e.source, target: e.target }))

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(65))
      .force('charge', d3.forceManyBody().strength(-180).theta(0.9))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(18))
      .alphaDecay(0.06)
      .velocityDecay(0.4)

    simRef.current = simulation

    let transform = d3.zoomIdentity
    let hasFitted = false

    function draw() {
      ctx.save()
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, width, height)
      ctx.translate(transform.x, transform.y)
      ctx.scale(transform.k, transform.k)

      ctx.strokeStyle = '#333'
      ctx.lineWidth = 0.8
      ctx.globalAlpha = 0.5
      for (const l of links) {
        ctx.beginPath()
        ctx.moveTo(l.source.x, l.source.y)
        ctx.lineTo(l.target.x, l.target.y)
        ctx.stroke()
        const dx = l.target.x - l.source.x, dy = l.target.y - l.source.y
        const len = Math.sqrt(dx * dx + dy * dy)
        if (len > 20) {
          const ux = dx / len, uy = dy / len
          const r = l.target.id === graphData.center ? 12 : 8
          const ax = l.target.x - ux * (r + 3), ay = l.target.y - uy * (r + 3)
          ctx.beginPath()
          ctx.moveTo(ax - uy * 3 - ux * 5, ay + ux * 3 - uy * 5)
          ctx.lineTo(ax, ay)
          ctx.lineTo(ax + uy * 3 - ux * 5, ay - ux * 3 - uy * 5)
          ctx.stroke()
        }
      }
      ctx.globalAlpha = 1

      for (const n of nodes) {
        const isC = n.id === graphData.center
        const r = isC ? 12 : 8
        ctx.beginPath()
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2)
        ctx.fillStyle = TYPE_COLORS[n.chunk_type] || '#888'
        ctx.fill()
        ctx.strokeStyle = isC ? '#fff' : '#1a1a2e'
        ctx.lineWidth = isC ? 2.5 : 1
        ctx.stroke()
      }

      if (transform.k > 0.6 || nodes.length < 50) {
        ctx.textAlign = 'center'
        ctx.textBaseline = 'bottom'
        ctx.fillStyle = '#bbb'
        ctx.font = '9px monospace'
        for (const n of nodes) {
          ctx.fillText(n.id, n.x, n.y - (n.id === graphData.center ? 15 : 11))
        }
      }

      ctx.restore()
    }

    const zoomBehavior = d3.zoom()
      .scaleExtent([0.05, 5])
      .filter((event) => {
        if (event.type === 'wheel') return event.ctrlKey || event.metaKey
        return !event.button
      })
      .on('zoom', (event) => {
        transform = event.transform
        draw()
      })
    d3.select(canvas).call(zoomBehavior)
    zoomRef.current = zoomBehavior

    simulation.on('tick', () => {
      draw()
      if (!hasFitted && simulation.alpha() < 0.3) {
        hasFitted = true
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
        for (const n of nodes) {
          if (n.x < minX) minX = n.x
          if (n.y < minY) minY = n.y
          if (n.x > maxX) maxX = n.x
          if (n.y > maxY) maxY = n.y
        }
        const padding = 50
        const bw = maxX - minX || 1
        const bh = maxY - minY || 1
        const scale = Math.min((width - padding * 2) / bw, (height - padding * 2) / bh, 2)
        const cx = (minX + maxX) / 2
        const cy = (minY + maxY) / 2
        const tx = width / 2 - cx * scale
        const ty = height / 2 - cy * scale
        transform = d3.zoomIdentity.translate(tx, ty).scale(scale)
        d3.select(canvas).call(zoomBehavior.transform, transform)
        draw()
      }
    })

    function findNode(mx, my) {
      const [x, y] = transform.invert([mx, my])
      for (let i = nodes.length - 1; i >= 0; i--) {
        const n = nodes[i], r = n.id === graphData.center ? 12 : 8
        if ((x - n.x) ** 2 + (y - n.y) ** 2 < (r + 3) ** 2) return n
      }
      return null
    }

    const tip = tooltipRef.current
    canvas.onmousemove = (e) => {
      const rect = canvas.getBoundingClientRect()
      const n = findNode(e.clientX - rect.left, e.clientY - rect.top)
      if (n) {
        tip.style.display = 'flex'
        tip.style.left = (e.clientX + 14) + 'px'
        tip.style.top = (e.clientY - 8) + 'px'
        tip.innerHTML = `<strong>${n.id}</strong><span>${n.chunk_type}</span><span class="tooltip-file">${n.file_path}:${n.start_line}-${n.end_line}</span>`
        canvas.style.cursor = 'pointer'
      } else {
        tip.style.display = 'none'
        canvas.style.cursor = 'grab'
      }
    }
    canvas.onmouseleave = () => { tip.style.display = 'none' }

    canvas.onclick = (e) => {
      const rect = canvas.getBoundingClientRect()
      const n = findNode(e.clientX - rect.left, e.clientY - rect.top)
      if (n && onNodeClick) onNodeClick(n.id)
    }

    let dragNode = null
    d3.select(canvas).call(
      d3.drag()
        .container(canvas)
        .subject((event) => findNode(d3.pointer(event, canvas)[0], d3.pointer(event, canvas)[1]))
        .on('start', (event) => {
          dragNode = event.subject
          if (!dragNode) return
          if (!event.active) simulation.alphaTarget(0.3).restart()
          dragNode.fx = dragNode.x; dragNode.fy = dragNode.y
        })
        .on('drag', (event) => {
          if (!dragNode) return
          const [x, y] = transform.invert([event.sourceEvent.offsetX, event.sourceEvent.offsetY])
          dragNode.fx = x; dragNode.fy = y
        })
        .on('end', (event) => {
          if (!dragNode) return
          if (!event.active) simulation.alphaTarget(0)
          dragNode.fx = null; dragNode.fy = null
          dragNode = null
        })
    )

    return () => simulation.stop()
  }, [graphData, onNodeClick])

  return (
    <>
      <div className="graph-container graph-container-full">
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%' }} />
      </div>
      <div ref={tooltipRef} className="graph-tooltip" style={{ display: 'none' }} />
    </>
  )
}

const Graph3D = ({ graphData, onNodeClick }) => {
  const graphRef = useRef()
  const containerRef = useRef()
  const [fgData, setFgData] = useState({ nodes: [], links: [] })
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 })
  const autoRotateRef = useRef(true)
  const resumeTimerRef = useRef(null)
  const ForceGraph3DRef = useRef(null)
  const [loaded, setLoaded] = useState(false)

  // Lazy-load the heavy 3D lib
  useEffect(() => {
    import('react-force-graph-3d').then((mod) => {
      ForceGraph3DRef.current = mod.default
      setLoaded(true)
    })
  }, [])

  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        if (rect.width > 0 && rect.height > 0) {
          setDimensions({ width: rect.width, height: rect.height })
        }
      }
    }
    // Measure immediately, then again after a frame to catch layout
    measure()
    const raf = requestAnimationFrame(measure)
    const timer = setTimeout(measure, 100)
    window.addEventListener('resize', measure)
    return () => {
      window.removeEventListener('resize', measure)
      cancelAnimationFrame(raf)
      clearTimeout(timer)
    }
  }, [loaded])

  // Pause rotation on interaction
  useEffect(() => {
    const pause = () => {
      autoRotateRef.current = false
      clearTimeout(resumeTimerRef.current)
      resumeTimerRef.current = setTimeout(() => { autoRotateRef.current = true }, 3000)
    }
    const onWheel = (e) => {
      if (!e.ctrlKey && !e.metaKey) { e.stopPropagation(); return }
      pause()
    }
    const el = containerRef.current
    if (!el) return
    el.addEventListener('wheel', onWheel, true)
    el.addEventListener('pointerdown', pause)
    return () => {
      el.removeEventListener('wheel', onWheel, true)
      el.removeEventListener('pointerdown', pause)
      clearTimeout(resumeTimerRef.current)
    }
  })

  useEffect(() => {
    if (!graphData) return
    const edgeSet = new Set()
    const nodes = Object.entries(graphData.nodes).map(([name, info]) => ({
      id: name, ...info,
      color: TYPE_COLORS[info.chunk_type] || '#888',
      isCenter: name === graphData.center,
    }))
    const links = graphData.edges
      .filter(e => {
        const key = `${e.source}->${e.target}`
        if (edgeSet.has(key)) return false
        edgeSet.add(key)
        return graphData.nodes[e.source] && graphData.nodes[e.target]
      })
      .map(e => ({ source: e.source, target: e.target }))
    setFgData({ nodes, links })
  }, [graphData])

  useEffect(() => {
    if (!graphRef.current) return

    // Disable middle-click entirely, right-click = pan
    const controls = graphRef.current.controls()
    if (controls) {
      controls.mouseButtons = {
        LEFT: 0,    // rotate
        MIDDLE: -1, // disabled
        RIGHT: 2,   // pan
      }
    }

    // Fit first, then start rotating at whatever distance the camera ended up
    const fitTimer = setTimeout(() => {
      if (graphRef.current) graphRef.current.zoomToFit(400, 60)
    }, 500)

    const angle = { value: 0 }
    const interval = setInterval(() => {
      if (!autoRotateRef.current || !graphRef.current) return
      const cam = graphRef.current.cameraPosition()
      const dist = Math.sqrt(cam.x * cam.x + cam.z * cam.z) || 200
      angle.value += Math.PI / 600
      graphRef.current.cameraPosition({
        x: dist * Math.sin(angle.value),
        y: cam.y,
        z: dist * Math.cos(angle.value),
      })
    }, 30)

    return () => { clearInterval(interval); clearTimeout(fitTimer) }
  }, [fgData, loaded])

  const ForceGraph3D = ForceGraph3DRef.current
  if (!loaded || !ForceGraph3D) return <div className="loading">Loading 3D engine...</div>

  return (
    <div className="graph-container graph-container-full" ref={containerRef}>
      {fgData.nodes.length > 0 && (
        <ForceGraph3D
          ref={graphRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={fgData}
          backgroundColor="#00000000"
          nodeColor={n => n.color}
          nodeVal={n => n.isCenter ? 6 : 2}
          nodeLabel={n => `${n.id} (${n.chunk_type}) — ${n.file_path}:${n.start_line}-${n.end_line}`}
          nodeOpacity={0.9}
          linkColor={() => 'rgba(0, 242, 255, 0.5)'}
          linkWidth={1.5}
          linkDirectionalArrowLength={5}
          linkDirectionalArrowRelPos={1}
          linkDirectionalArrowColor={() => 'rgba(0, 242, 255, 0.7)'}
          linkOpacity={0.6}
          onNodeClick={(node) => onNodeClick && onNodeClick(node.id)}
          enableNodeDrag={true}
          enableNavigationControls={true}
          showNavInfo={false}
        />
      )}
    </div>
  )
}

export default function DependencyGraph() {
  const [center, setCenter] = useState('NASTRN')
  const [depth, setDepth] = useState(1)
  const [graphData, setGraphData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [is3D, setIs3D] = useState(false)

  const loadGraph = useCallback(async (name, d) => {
    const nodeName = name || center
    if (!nodeName.trim()) return
    setLoading(true)
    setError(null)

    try {
      const data = await apiPost('/api/graph/subgraph', {
        name: nodeName,
        depth: d ?? depth,
        include_common: false,
      })
      if (data.error) {
        setError(data.error)
        setGraphData(null)
      } else {
        setGraphData(data)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [center, depth])

  useEffect(() => { loadGraph('NASTRN', 1) }, [])

  const handleNodeClick = useCallback((id) => {
    setCenter(id)
    loadGraph(id, depth)
  }, [depth, loadGraph])

  return (
    <div className="graph-tab">
      <div className="graph-controls">
        <div className="graph-search">
          <Autocomplete value={center} onChange={setCenter} placeholder="Search routine..." />
          <button onClick={() => loadGraph()} disabled={loading}>
            {loading ? 'Loading...' : 'Go'}
          </button>
        </div>
        <div className="graph-depth">
          <label>Depth: {depth}</label>
          <input type="range" min="1" max="3" value={depth}
            onChange={(e) => { const d = +e.target.value; setDepth(d); loadGraph(center, d) }} />
        </div>
        <button
          className={`graph-fit ${is3D ? 'active' : ''}`}
          onClick={() => setIs3D(!is3D)}
          style={is3D ? { borderColor: 'var(--cyan)', color: 'var(--cyan)' } : {}}
        >
          {is3D ? '3D' : '2D'}
        </button>
        <button className="graph-reset" onClick={() => { setCenter('NASTRN'); setDepth(1); loadGraph('NASTRN', 1) }}>
          Reset
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {graphData && (
        <div className="graph-info">
          <span>{graphData.node_count} nodes</span>
          <span>{graphData.edge_count} edges</span>
          <span style={{ opacity: 0.5 }}>
            {is3D ? 'Drag to orbit · Ctrl+scroll to zoom' : 'Ctrl+scroll to zoom · Drag to pan'}
          </span>
          <span className="graph-legend">
            {Object.entries(TYPE_COLORS).map(([type, color]) => (
              <span key={type} className="legend-item">
                <span className="legend-dot" style={{ background: color }} />
                {type}
              </span>
            ))}
          </span>
        </div>
      )}

      {graphData && !is3D && <Graph2D graphData={graphData} onNodeClick={handleNodeClick} />}
      {graphData && is3D && <Graph3D graphData={graphData} onNodeClick={handleNodeClick} />}
    </div>
  )
}
