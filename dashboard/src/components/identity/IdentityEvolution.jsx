import { useState } from 'react'
import Badge from '../ui/Badge'
import IdentityInspector from '../explain/IdentityInspector'

function DiffRow({ label, before, after, format = 'pct' }) {
  const beforeVal = before != null ? (format === 'pct' ? Math.round(before * 100) : before) : null
  const afterVal = after != null ? (format === 'pct' ? Math.round(after * 100) : after) : null
  const delta = beforeVal != null && afterVal != null ? afterVal - beforeVal : null
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: 13 }}>
      <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {beforeVal != null && <span style={{ color: 'var(--text-muted)' }}>{beforeVal}{format === 'pct' ? '%' : ''}</span>}
        <span style={{ color: 'var(--text-muted)' }}>→</span>
        {afterVal != null && <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{afterVal}{format === 'pct' ? '%' : ''}</span>}
        {delta != null && delta !== 0 && (
          <span style={{
            fontSize: 12, fontWeight: 600,
            color: delta > 0 ? 'var(--emerald-400)' : 'var(--rose-400)',
            background: delta > 0 ? 'rgba(16,185,129,0.1)' : 'rgba(244,63,94,0.1)',
            padding: '1px 6px', borderRadius: 4,
          }}>
            {delta > 0 ? '+' : ''}{delta}{format === 'pct' ? '%' : ''}
          </span>
        )}
      </div>
    </div>
  )
}

function TopicDiff({ title, added, removed, color }) {
  if (!added?.length && !removed?.length) return null
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>{title}</div>
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        {added?.map((t, i) => (
          <span key={i} style={{
            padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 500,
            background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.25)',
            color: 'var(--emerald-400)',
          }}>+ {typeof t === 'string' ? t : t.topic || t.name || t}</span>
        ))}
        {removed?.map((t, i) => (
          <span key={i} style={{
            padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 500,
            background: 'rgba(244,63,94,0.15)', border: '1px solid rgba(244,63,94,0.25)',
            color: 'var(--rose-400)',
          }}>− {typeof t === 'string' ? t : t.topic || t.name || t}</span>
        ))}
      </div>
    </div>
  )
}

function SnapshotCard({ snap, prev, index, total, onInspect }) {
  const addedTopics = prev ? (snap.dominant_topics || []).filter(t => {
    const ts = typeof t === 'string' ? t : t.topic || t.name
    return !(prev.dominant_topics || []).some(p => (typeof p === 'string' ? p : p.topic || p.name) === ts)
  }) : snap.dominant_topics || []

  const removedTopics = prev ? (prev.dominant_topics || []).filter(t => {
    const ts = typeof t === 'string' ? t : t.topic || t.name
    return !(snap.dominant_topics || []).some(p => (typeof p === 'string' ? p : p.topic || p.name) === ts)
  }) : []

  const ver = snap.identity_version || snap.snapshot_version || index + 1
  const isLast = index === total - 1

  return (
    <div style={{ display: 'flex', gap: 16, position: 'relative' }}>
      {/* Timeline connector */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 32, flexShrink: 0 }}>
        <div style={{
          width: 20, height: 20, borderRadius: 10, flexShrink: 0,
          background: isLast ? 'var(--accent-gradient)' : 'var(--indigo-500)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 9, color: 'white', fontWeight: 700, zIndex: 1,
        }}>
          {isLast ? '✓' : ver}
        </div>
        {index < total - 1 && (
          <div style={{ width: 2, flex: 1, background: 'var(--border-subtle)', margin: '4px 0' }} />
        )}
      </div>

      {/* Content */}
      <div style={{
        flex: 1, padding: 16, borderRadius: 12, marginBottom: 12,
        background: isLast ? 'rgba(99,102,241,0.06)' : 'rgba(0,0,0,0.15)',
        border: `1px solid ${isLast ? 'rgba(99,102,241,0.2)' : 'var(--border-subtle)'}`,
        cursor: 'pointer', transition: 'all 0.15s',
      }}
        onClick={() => onInspect?.(snap.identity_id || snap.snapshot_id)}
        onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(99,102,241,0.3)'}
        onMouseLeave={e => e.currentTarget.style.borderColor = isLast ? 'rgba(99,102,241,0.2)' : 'var(--border-subtle)'}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div>
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
              Version {ver}
            </span>
            {isLast && <Badge variant="indigo" style={{ marginLeft: 8 }}>Current</Badge>}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {snap.snapshot_timestamp ? new Date(snap.snapshot_timestamp).toLocaleDateString() : '--'}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 8 }}>
          <DiffRow label="Confidence" before={prev?.overall_confidence} after={snap.overall_confidence} />
          <DiffRow label="Completeness" before={prev?.identity_completeness} after={snap.identity_completeness} />
        </div>

        <TopicDiff title="Topic Changes" added={addedTopics} removed={removedTopics} />

        {(snap.dominant_topics || []).length > 0 && (
          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Topics</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {(snap.dominant_topics || []).map((t, i) => (
                <Badge key={i} variant="indigo">
                  {typeof t === 'string' ? t : t.topic || t.name || JSON.stringify(t)}
                </Badge>
              ))}
            </div>
          </div>
        )}

        <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
          Click to inspect →
        </div>
      </div>
    </div>
  )
}

export default function IdentityEvolution({ snapshots }) {
  const [inspectingId, setInspectingId] = useState(null)
  const sorted = [...(snapshots || [])].sort((a, b) => {
    const tA = new Date(a.snapshot_timestamp || 0).getTime()
    const tB = new Date(b.snapshot_timestamp || 0).getTime()
    return tA - tB
  })

  if (sorted.length < 2) {
    return (
      <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>
        At least 2 snapshots needed for evolution tracking
      </div>
    )
  }

  const first = sorted[0]
  const last = sorted[sorted.length - 1]
  const totalDelta = last.overall_confidence != null && first.overall_confidence != null
    ? Math.round((last.overall_confidence - first.overall_confidence) * 100) : null

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
        <div style={{ padding: 14, borderRadius: 10, background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.15)', textAlign: 'center' }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--indigo-400)' }}>{sorted.length}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Snapshots</div>
        </div>
        <div style={{ padding: 14, borderRadius: 10, background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.15)', textAlign: 'center' }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: totalDelta > 0 ? 'var(--emerald-400)' : totalDelta < 0 ? 'var(--rose-400)' : 'var(--text-secondary)' }}>
            {totalDelta != null ? `${totalDelta > 0 ? '+' : ''}${totalDelta}%` : '--'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Confidence Change</div>
        </div>
        <div style={{ padding: 14, borderRadius: 10, background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.15)', textAlign: 'center' }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--violet-400)' }}>
            v{first.identity_version || 1} → v{last.identity_version || sorted.length}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Version Range</div>
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        {sorted.map((snap, i) => (
          <SnapshotCard
            key={snap.snapshot_id || i}
            snap={snap}
            prev={i > 0 ? sorted[i - 1] : null}
            index={i}
            total={sorted.length}
            onInspect={setInspectingId}
          />
        ))}
      </div>

      {inspectingId && (
        <IdentityInspector identityId={inspectingId} onClose={() => setInspectingId(null)} />
      )}
    </div>
  )
}
