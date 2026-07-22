import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeftIcon, XIcon } from '../../icons/icons'
import { api } from '../../api/client'

function Badge({ variant = 'neutral', children }) {
  const colors = {
    emerald: { bg: 'rgba(16,185,129,0.1)', text: 'var(--emerald-400)' },
    amber: { bg: 'rgba(245,158,11,0.1)', text: 'var(--amber-400)' },
    rose: { bg: 'rgba(244,63,94,0.1)', text: 'var(--rose-400)' },
    indigo: { bg: 'rgba(99,102,241,0.1)', text: 'var(--indigo-400)' },
    neutral: { bg: 'rgba(148,163,184,0.1)', text: 'var(--text-muted)' },
  }
  const c = colors[variant] || colors.neutral
  return <span style={{ display: 'inline-flex', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 500, background: c.bg, color: c.text }}>{children}</span>
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      {children}
    </div>
  )
}

export default function EvidenceDrawer({ evidenceId, onClose }) {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!evidenceId) return
    setLoading(true)
    api.getEvidenceDetail(evidenceId)
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [evidenceId])

  useEffect(() => { document.body.style.overflow = 'hidden'; return () => { document.body.style.overflow = '' }}, [])

  if (!evidenceId) return null

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 999, display: 'flex', justifyContent: 'flex-end', animation: 'fadeIn 0.2s ease-out both' }}>
      <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)' }} onClick={onClose} />

      <div style={{
        width: 560, maxWidth: '90vw', height: '100vh',
        background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border-strong)',
        display: 'flex', flexDirection: 'column', animation: 'slideIn 0.3s ease-out both',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>
          <button onClick={onClose} style={{ width: 32, height: 32, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <ChevronLeftIcon />
          </button>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700 }}>Evidence Detail</h2>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>ID: {evidenceId?.slice(0, 16)}...</p>
          </div>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
          {loading && <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Loading...</div>}

          {data?.error && <div style={{ textAlign: 'center', padding: 60, color: 'var(--rose-400)' }}>{data.error}</div>}

          {data?.evidence && (
            <>
              <Field label="Summary">
                <div style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{data.evidence.explanation || data.evidence.evidence_id}</div>
              </Field>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                <Field label="Type">
                  <Badge variant={
                    data.evidence.evidence_type === 'behavioral' ? 'emerald' :
                    data.evidence.evidence_type === 'temporal' ? 'amber' :
                    data.evidence.evidence_type === 'topical' ? 'indigo' : 'neutral'
                  }>
                    {data.evidence.evidence_type}
                  </Badge>
                </Field>
                <Field label="Confidence">
                  <div style={{ fontSize: 18, fontWeight: 700, color: data.evidence.confidence > 0.7 ? 'var(--emerald-400)' : data.evidence.confidence > 0.4 ? 'var(--amber-400)' : 'var(--rose-400)' }}>
                    {data.evidence.confidence ? `${Math.round(data.evidence.confidence * 100)}%` : '--'}
                  </div>
                </Field>
                <Field label="Weight">{data.evidence.weight?.toFixed(3) || '--'}</Field>
                <Field label="Net Confidence">{data.evidence.net_confidence != null ? `${Math.round(data.evidence.net_confidence * 100)}%` : '--'}</Field>
              </div>

              <Field label="Source Events">
                <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{data.evidence.source_event_ids?.length || 0} events</div>
              </Field>

              <Field label="Linked Behavior Objects">
                {data.behavior_objects?.length > 0 ? data.behavior_objects.map((bo, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', borderRadius: 6, background: 'rgba(148,163,184,0.04)', marginBottom: 4, fontSize: 13 }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{bo.topic}</span>
                    <span style={{ color: 'var(--text-muted)' }}>{bo.importance_score?.toFixed(2)}</span>
                  </div>
                )) : <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>None linked</span>}
              </Field>

              <Field label="Related Inferences">
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {data.inferences?.slice(0, 5).map((inf, i) => (
                    <button key={i} onClick={() => navigate(`/evidence?inference_id=${inf.inference_id}`)} style={{ padding: '4px 10px', borderRadius: 6, fontSize: 11, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', color: 'var(--indigo-400)', cursor: 'pointer' }}>
                      {inf.label || inf.inference_type || inf.inference_id?.slice(0, 12)}
                    </button>
                  ))}
                </div>
              </Field>

              <Field label="Related Memories">
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {data.memories?.slice(0, 5).map((mem, i) => (
                    <button key={i} onClick={() => navigate(`/memory?memory_id=${mem.memory_id}`)} style={{ padding: '4px 10px', borderRadius: 6, fontSize: 11, background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)', color: 'var(--violet-400)', cursor: 'pointer' }}>
                      {mem.memory_type} · {(mem.content || '').slice(0, 30)}
                    </button>
                  ))}
                </div>
              </Field>

              <Field label="Identity Traits">
                <div style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.5 }}>
                  {data.identity_traits?.dominant_topics?.length > 0
                    ? data.identity_traits.dominant_topics.join(', ')
                    : 'No traits available'}
                </div>
              </Field>

              {data.counter_evidence?.length > 0 && (
                <Field label="Counter Evidence">
                  {data.counter_evidence.map((ce, i) => (
                    <div key={i} style={{ padding: '6px 8px', borderRadius: 6, background: 'rgba(244,63,94,0.06)', marginBottom: 4, fontSize: 12, color: 'var(--rose-400)' }}>
                      {ce.explanation || ce.evidence_id}
                    </div>
                  ))}
                </Field>
              )}

              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 16 }}>
                {data.evidence.evidence_id && (
                  <>
                    <button onClick={() => { onClose(); navigate(`/trace?trace_id=${data.evidence.evidence_id}`) }}
                      style={{ padding: '6px 14px', borderRadius: 8, fontSize: 12, background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)', color: 'var(--emerald-400)', cursor: 'pointer' }}>
                      🔍 Find in Trace
                    </button>
                    <button onClick={() => { onClose(); navigate(`/chat?evidence=${data.evidence.evidence_id}`) }}
                      style={{ padding: '6px 14px', borderRadius: 8, fontSize: 12, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', color: 'var(--indigo-400)', cursor: 'pointer' }}>
                      💬 Ask in Chat
                    </button>
                  </>
                )}
              </div>

              <Field label="Raw JSON">
                <pre style={{ fontSize: 11, color: 'var(--text-muted)', background: 'rgba(0,0,0,0.3)', padding: 12, borderRadius: 8, overflow: 'auto', maxHeight: 200 }}>
                  {JSON.stringify(data.evidence, null, 2)}
                </pre>
              </Field>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
