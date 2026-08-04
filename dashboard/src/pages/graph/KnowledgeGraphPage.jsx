import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import ForceGraph3D from 'react-force-graph-3d'
import { api } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import LoadingSkeleton from '../../components/ui/LoadingSkeleton'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'

const PLATFORM_COLOR = {
  instagram: '#ec4899',
  youtube: '#f43f5e',
  both: '#a855f7',
  none: '#818cf8',
}
const CREATOR_COLOR = '#64748b'

function colorForTopic(node) {
  const platforms = node.platforms || []
  if (platforms.length >= 2) return PLATFORM_COLOR.both
  if (platforms[0] === 'instagram') return PLATFORM_COLOR.instagram
  if (platforms[0] === 'youtube') return PLATFORM_COLOR.youtube
  return PLATFORM_COLOR.none
}

function NodeDetail({ node, onClose }) {
  if (!node) return null
  const isTopic = node.group === 'topic'
  return (
    <GlassCard
      padding="lg"
      style={{
        position: 'absolute', top: 16, right: 16, width: 300, zIndex: 10,
        background: 'rgba(15,23,42,0.92)', backdropFilter: 'blur(16px)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div>
          <Badge variant={isTopic ? 'indigo' : 'neutral'}>{isTopic ? 'Topic' : 'Creator'}</Badge>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 8, color: 'var(--text-primary)' }}>{node.label}</h3>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 18, lineHeight: 1 }}>×</button>
      </div>

      {isTopic ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>Importance</span>
            <span style={{ color: 'var(--text-secondary)' }}>{Math.round(node.importance * 100)}%</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>Confidence</span>
            <span style={{ color: 'var(--text-secondary)' }}>{Math.round(node.confidence * 100)}%</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>Lifecycle</span>
            <span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{node.lifecycle}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>Events</span>
            <span style={{ color: 'var(--text-secondary)' }}>{node.event_count}</span>
          </div>
          {node.platforms?.length > 0 && (
            <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
              {node.platforms.map(p => <Badge key={p} variant="neutral">{p === 'youtube' ? '▶️' : '📸'} {p}</Badge>)}
            </div>
          )}
          {node.keywords?.length > 0 && (
            <div style={{ marginTop: 6, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {node.keywords.map((k, i) => <Badge key={i} variant="amber">{k}</Badge>)}
            </div>
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>Topics connected</span>
            <span style={{ color: 'var(--text-secondary)' }}>{node.topic_count}</span>
          </div>
          {node.platforms?.length > 0 && (
            <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
              {node.platforms.map(p => <Badge key={p} variant="neutral">{p === 'youtube' ? '▶️' : '📸'} {p}</Badge>)}
            </div>
          )}
        </div>
      )}
    </GlassCard>
  )
}

export default function KnowledgeGraphPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)
  const [search, setSearch] = useState('')
  const [size, setSize] = useState({ width: 800, height: 600 })
  const containerRef = useRef(null)
  const fgRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api.getKnowledgeGraph().then(d => { if (!cancelled) setData(d) })
      .catch(err => { if (!cancelled) setError(err?.response?.data?.detail || err.message || 'Failed to load graph') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect
      setSize({ width: Math.max(300, width), height: Math.max(300, height) })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] }
    return { nodes: data.nodes, links: data.links }
  }, [data])

  const matchCount = useMemo(() => {
    if (!search.trim() || !data) return 0
    const q = search.trim().toLowerCase()
    return data.nodes.filter(n => n.label.toLowerCase().includes(q)).length
  }, [search, data])

  const runSearch = useCallback(() => {
    if (!search.trim() || !data || !fgRef.current) return
    const q = search.trim().toLowerCase()
    const match = data.nodes.find(n => n.label.toLowerCase().includes(q))
    if (match && typeof match.x === 'number') {
      const distance = 120
      const ratio = 1 + distance / Math.hypot(match.x, match.y, match.z || 1)
      fgRef.current.cameraPosition(
        { x: match.x * ratio, y: match.y * ratio, z: (match.z || 0) * ratio },
        match, 1000
      )
      setSelected(match)
    }
  }, [search, data])

  const stats = useMemo(() => {
    if (!data) return null
    const topics = data.nodes.filter(n => n.group === 'topic').length
    const creators = data.nodes.filter(n => n.group === 'creator').length
    return { topics, creators, links: data.links.length }
  }, [data])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 68, height: 68, flexShrink: 0, margin: '-8px 0' }}>
            <CharacterCreature3D size={68} variant="orbital" confidence={stats?.topics ? 0.7 : 0.35} thinking={loading} showLabels={false} />
          </div>
          <div>
            <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
              Living Knowledge Graph
            </h1>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>
              {stats ? `${stats.topics} topics · ${stats.creators} creators · ${stats.links} real connections` : 'Every topic and creator that actually shaped your identity'}
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && runSearch()}
            placeholder="Find a topic or creator…"
            style={{
              padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border-subtle)',
              background: 'rgba(148,163,184,0.04)', color: 'var(--text-primary)', fontSize: 13, width: 220,
            }}
          />
          <button
            onClick={runSearch}
            disabled={!matchCount}
            style={{
              padding: '8px 16px', borderRadius: 8, border: 'none',
              background: matchCount ? 'var(--accent-gradient)' : 'rgba(148,163,184,0.15)',
              color: 'white', fontSize: 13, fontWeight: 600, cursor: matchCount ? 'pointer' : 'default',
            }}
          >
            Fly to
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 12, fontSize: 12, color: 'var(--text-tertiary)' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}><span style={{ width: 8, height: 8, borderRadius: 4, background: PLATFORM_COLOR.instagram, display: 'inline-block' }} /> Instagram topic</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}><span style={{ width: 8, height: 8, borderRadius: 4, background: PLATFORM_COLOR.youtube, display: 'inline-block' }} /> YouTube topic</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}><span style={{ width: 8, height: 8, borderRadius: 4, background: PLATFORM_COLOR.both, display: 'inline-block' }} /> Cross-platform</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}><span style={{ width: 8, height: 8, borderRadius: 4, background: CREATOR_COLOR, display: 'inline-block' }} /> Creator</span>
      </div>

      <div ref={containerRef} style={{ position: 'relative', flex: 1, borderRadius: 16, overflow: 'hidden', border: '1px solid var(--border-subtle)', background: 'radial-gradient(circle at 50% 50%, rgba(30,27,75,0.4), rgba(2,6,23,0.6))' }}>
        {loading && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <LoadingSkeleton type="chart" height={400} />
          </div>
        )}
        {!loading && error && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <GlassCard><div style={{ color: '#f87171', fontSize: 13 }}>{error}</div></GlassCard>
          </div>
        )}
        {!loading && !error && data && data.nodes.length === 0 && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <GlassCard>
              <div style={{ textAlign: 'center', padding: '16px 24px', color: 'var(--text-tertiary)' }}>
                No behavior objects yet — browse with the extension active or run a demo seed from Import.
              </div>
            </GlassCard>
          </div>
        )}
        {!loading && !error && data && data.nodes.length > 0 && (
          <ForceGraph3D
            ref={fgRef}
            graphData={graphData}
            width={size.width}
            height={size.height}
            backgroundColor="rgba(0,0,0,0)"
            nodeId="id"
            nodeLabel={n => `${n.label}${n.group === 'topic' ? ` · importance ${Math.round(n.importance * 100)}%` : ` · ${n.topic_count} topics`}`}
            nodeVal={n => n.group === 'topic' ? 2 + n.importance * 14 : 1 + n.topic_count * 0.6}
            nodeColor={n => n.group === 'topic' ? colorForTopic(n) : CREATOR_COLOR}
            nodeOpacity={0.92}
            linkColor={l => l.kind === 'creates' ? 'rgba(129,140,248,0.35)' : 'rgba(245,158,11,0.25)'}
            linkWidth={l => l.kind === 'related' ? Math.min(2, (l.weight || 1) * 0.4) : 0.6}
            linkDirectionalParticles={l => l.kind === 'creates' ? 1 : 0}
            linkDirectionalParticleWidth={1.4}
            linkDirectionalParticleSpeed={0.004}
            onNodeClick={setSelected}
            onBackgroundClick={() => setSelected(null)}
            enableNodeDrag={true}
            showNavInfo={false}
          />
        )}
        <NodeDetail node={selected} onClose={() => setSelected(null)} />
      </div>
    </div>
  )
}
