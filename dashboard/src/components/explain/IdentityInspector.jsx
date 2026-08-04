import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeftIcon } from '../../icons/icons'
import { api } from '../../api/client'

function Badge({ variant = 'neutral', children }) {
  const colors = {
    emerald: { bg: 'rgba(16,185,129,0.1)', text: 'var(--emerald-400)' },
    amber: { bg: 'rgba(245,158,11,0.1)', text: 'var(--amber-400)' },
    rose: { bg: 'rgba(244,63,94,0.1)', text: 'var(--rose-400)' },
    indigo: { bg: 'rgba(99,102,241,0.1)', text: 'var(--indigo-400)' },
    violet: { bg: 'rgba(139,92,246,0.1)', text: 'var(--violet-400)' },
    neutral: { bg: 'rgba(148,163,184,0.1)', text: 'var(--text-muted)' },
  }
  return <span style={{ display: 'inline-flex', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 500, background: colors[variant]?.bg, color: colors[variant]?.text }}>{children}</span>
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      {children}
    </div>
  )
}

function ContributionBar({ label, value, color }) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 2 }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{value}%</span>
      </div>
      <div style={{ height: 5, borderRadius: 3, background: 'var(--border-subtle)', overflow: 'hidden' }}>
        <div style={{ height: '100%', borderRadius: 3, width: `${value}%`, background: color, transition: 'width 0.6s ease' }} />
      </div>
    </div>
  )
}

export default function IdentityInspector({ identityId, onClose }) {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!identityId) return
    setLoading(true)
    api.getIdentityDetail(identityId)
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [identityId])

  useEffect(() => { document.body.style.overflow = 'hidden'; return () => { document.body.style.overflow = '' }}, [])

  if (!identityId) return null

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 999, display: 'flex', justifyContent: 'flex-end', animation: 'fadeIn 0.2s ease-out both' }}>
      <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)' }} onClick={onClose} />

      <div style={{
        width: 600, maxWidth: '90vw', height: '100vh',
        background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border-strong)',
        display: 'flex', flexDirection: 'column', animation: 'slideIn 0.3s ease-out both',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>
          <button onClick={onClose} style={{ width: 32, height: 32, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <ChevronLeftIcon />
          </button>
          <h2 style={{ fontSize: 16, fontWeight: 700 }}>Identity Inspector</h2>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
          {loading && <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Loading identity data...</div>}
          {data?.error && <div style={{ textAlign: 'center', padding: 60, color: 'var(--rose-400)' }}>{data.error}</div>}

          {data?.identity && (
            <>
              <Field label="Current Profile">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div style={{ padding: 12, borderRadius: 8, background: 'rgba(99,102,241,0.08)', textAlign: 'center' }}>
                    <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--indigo-400)' }}>
                      {data.identity.overall_confidence ? `${Math.round(data.identity.overall_confidence * 100)}%` : '--'}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Confidence</div>
                  </div>
                  <div style={{ padding: 12, borderRadius: 8, background: 'rgba(16,185,129,0.08)', textAlign: 'center' }}>
                    <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--emerald-400)' }}>
                      v{data.identity.identity_version || 1}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Version</div>
                  </div>
                </div>
              </Field>

              <Field label="Composition of Grounding Data">
                <div style={{ padding: 16, borderRadius: 10, background: 'rgba(0,0,0,0.2)' }}>
                  {data.grounding_composition && Object.entries(data.grounding_composition).map(([key, val]) => (
                    <ContributionBar
                      key={key}
                      label={key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                      value={val}
                      color={
                        key === 'behavior_objects' ? '#6366f1' :
                        key === 'evidence' ? '#10b981' :
                        key === 'reflections' ? '#8b5cf6' :
                        '#ec4899'
                      }
                    />
                  ))}
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10, lineHeight: 1.5 }}>
                    Real row counts behind this identity, by share — not a weighting of how much each category influenced its confidence score.
                  </p>
                </div>
              </Field>

              {data.snapshots?.length > 0 && (
                <Field label="Historical Snapshots">
                  {data.snapshots.slice(0, 5).map((snap, i) => (
                    <div key={i} style={{ padding: '8px 12px', borderRadius: 8, background: 'rgba(148,163,184,0.04)', marginBottom: 6, border: '1px solid var(--border-subtle)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                        <span style={{ color: 'var(--text-secondary)' }}>v{snap.identity_version}</span>
                        <span style={{ color: 'var(--text-muted)' }}>{Math.round(snap.overall_confidence * 100)}%</span>
                      </div>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {(snap.dominant_topics || []).slice(0, 4).map((t, j) => (
                          <Badge key={j} variant="indigo">{typeof t === 'string' ? t : t.topic || t.name}</Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </Field>
              )}

              <Field label="Dominant Topics">
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {data.topics && Object.entries(data.topics).sort((a, b) => b[1].total_importance - a[1].total_importance).slice(0, 8).map(([topic, stats], i) => (
                    <div key={i} style={{ padding: '6px 12px', borderRadius: 8, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.15)', fontSize: 12, color: 'var(--indigo-400)' }}>
                      {topic}
                      <span style={{ color: 'var(--text-muted)', marginLeft: 6 }}>{stats.count}</span>
                    </div>
                  ))}
                </div>
              </Field>

              <Field label="Evidence Contributing">
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {data.evidence?.slice(0, 8).map((ev, i) => (
                    <button key={i} onClick={() => navigate(`/evidence?evidence_id=${ev.evidence_id}`)}
                      style={{ padding: '4px 10px', borderRadius: 6, fontSize: 11, background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)', color: 'var(--emerald-400)', cursor: 'pointer' }}>
                      {ev.evidence_type} · {Math.round(ev.confidence * 100)}%
                    </button>
                  ))}
                </div>
              </Field>

              <Field label="Behavior Objects">
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {data.behavior_objects?.slice(0, 8).map((bo, i) => (
                    <button key={i} onClick={() => navigate(`/behavior?topic=${bo.unique_id}`)}
                      style={{ padding: '4px 10px', borderRadius: 6, fontSize: 11, background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)', color: 'var(--violet-400)', cursor: 'pointer' }}>
                      {bo.topic} · {(bo.importance_score || 0).toFixed(2)}
                    </button>
                  ))}
                </div>
              </Field>

              <Field label="Reflections">
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {data.reflections?.slice(0, 4).map((ref, i) => (
                    <button key={i} onClick={() => navigate(`/pipeline?reflection_id=${ref.reflection_id}`)}
                      style={{ padding: '4px 10px', borderRadius: 6, fontSize: 11, background: 'rgba(236,72,153,0.1)', border: '1px solid rgba(236,72,153,0.2)', color: 'var(--pink-400)', cursor: 'pointer' }}>
                      {(ref.summary || '').slice(0, 36)}
                    </button>
                  ))}
                </div>
              </Field>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
