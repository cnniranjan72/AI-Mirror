import { useMemo, useRef, useState, useEffect, lazy, Suspense } from 'react'
import Badge from '../ui/Badge'

// Lazy: react-force-graph-3d is ~710KB minified, and it is one element on a
// page that has other content worth showing first. Statically importing it
// made the whole route wait on that download before rendering anything.
const ForceGraph3D = lazy(() => import('react-force-graph-3d'))

const CATEGORY_COLOR = {
  reflections: '#818cf8',
  inferences: '#a78bfa',
  patterns: '#f472b6',
}
const CATEGORY_LABEL = {
  reflections: 'Reflection Memory',
  inferences: 'Semantic Memory',
  patterns: 'Pattern Memory',
}

/**
 * A real hierarchical tree of this user's memory: root -> category ->
 * individual entries. No synthetic data — reflections/inferences/patterns
 * are the exact same arrays MemoryPage's list view renders, just capped to
 * the top N by confidence per category so the tree stays readable.
 */
export default function MemoryTree({ reflections, inferences, patterns, height = 420 }) {
  const [selected, setSelected] = useState(null)
  const fgRef = useRef()
  const containerRef = useRef()
  const [width, setWidth] = useState(600)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(entries => setWidth(Math.max(300, entries[0].contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const graphData = useMemo(() => {
    const nodes = [{ id: 'root', label: 'You', group: 'root' }]
    const links = []

    const categories = [
      { key: 'reflections', items: reflections },
      { key: 'inferences', items: inferences },
      { key: 'patterns', items: patterns },
    ]

    for (const cat of categories) {
      if (!cat.items.length) continue
      const catId = `cat:${cat.key}`
      nodes.push({ id: catId, label: CATEGORY_LABEL[cat.key], group: 'category', category: cat.key, count: cat.items.length })
      links.push({ source: 'root', target: catId })

      const top = [...cat.items].sort((a, b) => (b.confidence || 0) - (a.confidence || 0)).slice(0, 8)
      top.forEach((item, i) => {
        const id = `${cat.key}:${item.reflection_id || item.inference_id || item.pattern_id || i}`
        nodes.push({
          id,
          label: (item.summary || item.description || `Entry ${i + 1}`).slice(0, 60),
          group: 'entry',
          category: cat.key,
          confidence: item.confidence || 0,
          full: item.summary || item.description || '',
        })
        links.push({ source: catId, target: id })
      })
    }

    return { nodes, links }
  }, [reflections, inferences, patterns])

  const hasData = graphData.nodes.length > 1

  if (!hasData) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
        No memory entries yet.
      </div>
    )
  }

  return (
    <div ref={containerRef} style={{ position: 'relative', height, borderRadius: 12, overflow: 'hidden', background: 'radial-gradient(circle at 50% 40%, rgba(30,27,75,0.4), rgba(2,6,23,0.5))' }}>
      {/* Fallback fills the graph's own box, so the surrounding layout does
          not reflow when the lazy chunk lands. */}
      <Suspense fallback={
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
          Loading graph…
        </div>
      }>
      <ForceGraph3D
        ref={fgRef}
        graphData={graphData}
        width={width}
        height={height}
        backgroundColor="rgba(0,0,0,0)"
        dagMode="radialout"
        dagLevelDistance={55}
        nodeId="id"
        nodeLabel={n => n.group === 'root' ? 'You' : n.label}
        nodeVal={n => n.group === 'root' ? 6 : n.group === 'category' ? 3 + Math.min(6, n.count * 0.4) : 1.5 + (n.confidence || 0) * 3}
        nodeColor={n => n.group === 'root' ? '#e2e8f0' : n.group === 'category' ? CATEGORY_COLOR[n.category] : `${CATEGORY_COLOR[n.category]}aa`}
        linkColor={() => 'rgba(148,163,184,0.25)'}
        linkWidth={0.6}
        onNodeClick={(n) => n.group === 'entry' && setSelected(n)}
        onBackgroundClick={() => setSelected(null)}
        enableNodeDrag={false}
        showNavInfo={false}
      />
      </Suspense>
      {selected && (
        <div style={{
          position: 'absolute', bottom: 12, left: 12, right: 12, padding: 12, borderRadius: 10,
          background: 'rgba(15,23,42,0.92)', backdropFilter: 'blur(8px)', border: '1px solid var(--border-subtle)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', flex: 1 }}>{selected.full || selected.label}</div>
            <Badge variant="indigo">{Math.round((selected.confidence || 0) * 100)}%</Badge>
          </div>
        </div>
      )}
    </div>
  )
}
