import { useState, useCallback } from 'react'
import { useReflections, useInferences, useBehaviorObjects } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'
import { BrainIcon, LayersIcon, SearchIcon } from '../../icons/icons'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'
import MemoryTree from '../../components/memory/MemoryTree'

const memoryTypes = [
  { key: 'reflections', label: 'Reflection Memory', icon: BrainIcon, color: '#6366f1' },
  { key: 'inferences', label: 'Semantic Memory', icon: LayersIcon, color: '#8b5cf6' },
  { key: 'patterns', label: 'Pattern Memory', icon: BrainIcon, color: '#ec4899' },
]

// A "pattern" is a behavior object with an established lifecycle trend — a
// recurring/growing/declining topic, not a one-off. Derived from real
// behavior-object data (no separate pattern store exists in the backend).
const PATTERN_STATES = new Set(['growing', 'stable', 'mature', 'declining'])

export default function MemoryPage() {
  const { data: reflections, loading: refLoading, error: refError, refetch: refetchRefs } = useReflections()
  const { data: inferences, loading: infLoading, error: infError, refetch: refetchInfs } = useInferences()
  const { data: behaviorObjects, loading: patLoading, error: patError, refetch: refetchBos } = useBehaviorObjects()
  const [search, setSearch] = useState('')
  const [activeTab, setActiveTab] = useState('all')

  const refs = Array.isArray(reflections) ? reflections : (reflections?.reflections || [])
  const infs = Array.isArray(inferences) ? inferences : (inferences?.inferences || [])
  const bos = Array.isArray(behaviorObjects) ? behaviorObjects : (behaviorObjects?.objects || [])
  const patterns = bos
    .filter(b => PATTERN_STATES.has(b.lifecycle_state))
    .sort((a, b) => (b.importance_score || 0) - (a.importance_score || 0))
    .map(b => ({
      pattern_id: b.unique_id,
      summary: `${b.topic}: ${b.lifecycle_state} pattern, ${Math.round((b.confidence_score || 0) * 100)}% confidence`,
      confidence: b.confidence_score,
    }))

  const filterItems = (items) => {
    if (!search) return items
    const q = search.toLowerCase()
    return items.filter(i => JSON.stringify(i).toLowerCase().includes(q))
  }

  const filteredRefs = filterItems(refs)
  const filteredInfs = filterItems(infs)
  const filteredPatterns = filterItems(patterns)

  const tabs = [
    { id: 'all', label: 'All Memory', count: refs.length + infs.length + patterns.length },
    { id: 'reflections', label: 'Reflections', count: refs.length },
    { id: 'inferences', label: 'Inferences', count: infs.length },
    { id: 'patterns', label: 'Patterns', count: patterns.length },
  ]

  const memoryLoading = refLoading || infLoading || patLoading
  const memoryError = refError || infError || patError
  const retryAll = useCallback(() => { refetchRefs(); refetchInfs(); refetchBos() }, [refetchRefs, refetchInfs, refetchBos])
  const avgPatternConfidence = patterns.length
    ? patterns.reduce((s, p) => s + (p.confidence || 0), 0) / patterns.length
    : 0.3

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 32 }}>
        <div style={{ width: 68, height: 68, flexShrink: 0, margin: '-8px 0' }}>
          <CharacterCreature3D
            size={68}
            variant="neural"
            confidence={avgPatternConfidence}
            topics={memoryTypes.map(m => m.label)}
            thinking={memoryLoading}
            showLabels={false}
          />
        </div>
        <div>
          <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Memory</h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Cognitive memory stores and retrieval</p>
        </div>
      </div>

      <AsyncState
        loading={memoryLoading}
        error={memoryError}
        onRetry={retryAll}
        empty={!memoryLoading && refs.length + infs.length + patterns.length === 0}
        emptyIcon="🧠"
        emptyTitle="No memory yet"
        emptyDescription="Reflections, inferences, and patterns build up as you browse with the extension enabled."
      >
      <div style={{ display: 'flex', gap: 16, marginBottom: 24, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 200, position: 'relative' }}>
          <div style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}><SearchIcon /></div>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search memory..."
            style={{
              width: '100%', padding: '10px 12px 10px 36px', borderRadius: 8,
              background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
              color: 'var(--text-primary)', fontSize: 14, outline: 'none',
            }}
          />
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
              padding: '6px 14px', borderRadius: 100, border: '1px solid var(--border-subtle)',
              background: activeTab === t.id ? 'rgba(99,102,241,0.15)' : 'transparent',
              color: activeTab === t.id ? 'var(--indigo-400)' : 'var(--text-tertiary)',
              fontSize: 13, fontWeight: 500, cursor: 'pointer',
            }}>
              {t.label} <span style={{ opacity: 0.6, marginLeft: 4 }}>{t.count}</span>
            </button>
          ))}
        </div>
      </div>

      <GlassCard gradient style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Memory Tree</h3>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              Every branch is real — reflections, inferences, and established behavior patterns, sized by confidence. Click a leaf.
            </p>
          </div>
          <Badge variant="indigo">{refs.length + infs.length + patterns.length} entries</Badge>
        </div>
        <MemoryTree reflections={refs} inferences={infs} patterns={patterns} height={420} />
      </GlassCard>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
        {memoryTypes.map(mt => (
          <GlassCard key={mt.key} gradient>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <div style={{ width: 32, height: 32, borderRadius: 8, background: `${mt.color}15`, border: `1px solid ${mt.color}30`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: mt.color }}>
                <mt.icon />
              </div>
              <div>
                <h4 style={{ fontSize: 14, fontWeight: 600 }}>{mt.label}</h4>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {mt.key === 'reflections' ? filteredRefs.length : mt.key === 'inferences' ? filteredInfs.length : filteredPatterns.length} entries
                </div>
              </div>
            </div>
            <div style={{ maxHeight: 240, overflow: 'auto' }}>
              {(mt.key === 'reflections' ? filteredRefs : mt.key === 'inferences' ? filteredInfs : filteredPatterns)
                .slice(0, 10).map((item, i) => (
                  <div key={item.reflection_id || item.inference_id || item.pattern_id || i} style={{
                    padding: '8px 0', borderBottom: '1px solid var(--border-subtle)',
                    animation: `fadeIn 0.3s ease-out ${i * 0.05}s both`,
                  }}>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500, marginBottom: 4 }}>
                      {item.summary || item.description || `Entry ${i + 1}`}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', gap: 8 }}>
                      {item.confidence != null && <span>Conf: {Math.round(item.confidence * 100)}%</span>}
                      {item.event_count && <span>{item.event_count} events</span>}
                    </div>
                  </div>
                ))}
              {mt.key === 'reflections' && filteredRefs.length === 0 && (
                <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>No reflections</div>
              )}
              {mt.key === 'patterns' && filteredPatterns.length === 0 && (
                <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>No established patterns yet</div>
              )}
            </div>
          </GlassCard>
        ))}
      </div>
      </AsyncState>
    </div>
  )
}
