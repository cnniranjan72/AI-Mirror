import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeftIcon } from '../../icons/icons'
import { api } from '../../api/client'

function Section({ title, icon, children, defaultOpen = true }) {
  return (
    <div style={{
      border: '1px solid var(--border-subtle)', borderRadius: 12,
      overflow: 'hidden', marginBottom: 12,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '12px 16px', background: 'rgba(0,0,0,0.2)',
        borderBottom: '1px solid var(--border-subtle)',
        fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)',
      }}>
        {icon}<span>{title}</span>
      </div>
      <div style={{ padding: 16 }}>
        {children}
      </div>
    </div>
  )
}

function Badge({ variant = 'neutral', children, style = {} }) {
  const colors = {
    emerald: { bg: 'rgba(16,185,129,0.1)', text: 'var(--emerald-400)' },
    amber: { bg: 'rgba(245,158,11,0.1)', text: 'var(--amber-400)' },
    rose: { bg: 'rgba(244,63,94,0.1)', text: 'var(--rose-400)' },
    indigo: { bg: 'rgba(99,102,241,0.1)', text: 'var(--indigo-400)' },
    neutral: { bg: 'rgba(148,163,184,0.1)', text: 'var(--text-muted)' },
  }
  const c = colors[variant] || colors.neutral
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 500,
      background: c.bg, color: c.text, ...style,
    }}>
      {children}
    </span>
  )
}

function ConfidenceBar({ value, label }) {
  const pct = value != null ? Math.round(value * 100) : 0
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{pct}%</span>
      </div>
      <div style={{ height: 4, borderRadius: 2, background: 'var(--border-subtle)', overflow: 'hidden' }}>
        <div style={{
          height: '100%', borderRadius: 2, width: `${pct}%`,
          background: pct > 70 ? 'var(--emerald-500)' : pct > 40 ? 'var(--amber-500)' : 'var(--rose-500)',
          transition: 'width 0.4s ease',
        }} />
      </div>
    </div>
  )
}

function LinkedChip({ label, to, icon }) {
  const navigate = useNavigate()
  return (
    <button
      onClick={() => navigate(to)}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        padding: '4px 10px', borderRadius: 6, fontSize: 11,
        background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)',
        color: 'var(--indigo-400)', cursor: 'pointer',
        transition: 'all 0.15s',
      }}
      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.2)' }}
      onMouseLeave={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.1)' }}
    >
      {icon}{label} →
    </button>
  )
}

function TimelineBar({ data }) {
  const total = Object.values(data).reduce((s, v) => s + v, 0) || 1
  const items = Object.entries(data).filter(([_, v]) => v > 0)
  return (
    <div style={{ display: 'flex', gap: 2, height: 24, borderRadius: 6, overflow: 'hidden' }}>
      {items.map(([key, val]) => (
        <div
          key={key}
          style={{
            flex: val / total, minWidth: 4,
            background: key === 'total' ? 'var(--indigo-500)' :
              ['emerald', 'amber', 'rose', 'indigo', 'violet', 'pink', 'cyan'][items.indexOf(key) % 7],
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 9, color: 'white', fontWeight: 600, overflow: 'hidden',
          }}
          title={`${key}: ${val}ms`}
        >
          {val / total > 0.15 ? `${Math.round(val)}ms` : ''}
        </div>
      ))}
    </div>
  )
}

export default function ExplainabilityPanel({ traceId, onClose }) {
  const navigate = useNavigate()
  useEffect(() => { document.body.style.overflow = 'hidden'; return () => { document.body.style.overflow = '' }}, [])

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!traceId) return
    setLoading(true)
    api.getExplain(traceId)
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [traceId])

  if (!traceId) return null

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 999,
      display: 'flex', justifyContent: 'flex-end',
      animation: 'fadeIn 0.2s ease-out both',
    }}>
      <div
        style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
        onClick={onClose}
      />

      <div style={{
        width: 640, maxWidth: '90vw', height: '100vh',
        background: 'var(--bg-secondary)',
        borderLeft: '1px solid var(--border-strong)',
        display: 'flex', flexDirection: 'column',
        animation: 'slideIn 0.3s ease-out both',
        position: 'relative',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button onClick={onClose} style={{
              width: 32, height: 32, borderRadius: 8,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)', cursor: 'pointer',
            }}>
              <ChevronLeftIcon />
            </button>
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 700 }}>Why did the AI say this?</h2>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                Trace: {traceId?.slice(0, 16)}...
              </p>
            </div>
          </div>
          <Badge variant={data?.success ? 'emerald' : 'rose'}>
            {data?.success ? 'Complete' : data ? 'Failed' : '...'}
          </Badge>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
          {loading && (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
              <div style={{ fontSize: 32, marginBottom: 16 }}>🔍</div>
              <div>Loading reasoning chain...</div>
            </div>
          )}

          {error && (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--rose-400)' }}>
              <div style={{ fontSize: 32, marginBottom: 16 }}>⚠️</div>
              <div>{error}</div>
            </div>
          )}

          {data && !data.error && (
            <>
              {/* Final Response */}
              <Section title="Final Response" icon={<span style={{ fontSize: 16 }}>💬</span>}>
                <div style={{
                  padding: 12, borderRadius: 8,
                  background: 'rgba(99,102,241,0.08)',
                  border: '1px solid rgba(99,102,241,0.15)',
                  fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6,
                }}>
                  {data.query}
                </div>
                {data.response && (
                  <div style={{
                    marginTop: 8, padding: 12, borderRadius: 8,
                    background: 'rgba(16,185,129,0.08)',
                    border: '1px solid rgba(16,185,129,0.15)',
                    fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6,
                  }}>
                    {data.response}
                  </div>
                )}
              </Section>

              {/* Identity Snapshot Used */}
              <Section title="Identity Snapshot" icon={<span style={{ fontSize: 16 }}>🧠</span>}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <ConfidenceBar value={data.identity?.confidence} label="Confidence" />
                  {data.identity?.completeness != null && (
                    <ConfidenceBar value={data.identity.completeness} label="Completeness" />
                  )}
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    <Badge variant="indigo">v{data.identity?.identity_version || '?'}</Badge>
                    <Badge variant="neutral">ID: {(data.identity?.snapshot_id || '').slice(0, 12)}</Badge>
                  </div>
                  {data.identity?.identity_id && (
                    <LinkedChip
                      label="View Identity Detail"
                      to={`/identity?identity_id=${data.identity.identity_id}`}
                      icon={<span>🧠</span>}
                    />
                  )}
                  {data.identity?.dominant_topics?.length > 0 && (
                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Dominant Topics</div>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {data.identity.dominant_topics.map((t, i) => (
                          <Badge key={i} variant="indigo">{typeof t === 'string' ? t : t.topic || t.name || JSON.stringify(t)}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </Section>

              {/* Evidence Used */}
              <Section title="Evidence Used" icon={<span style={{ fontSize: 16 }}>📊</span>}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {data.evidence?.items?.slice(0, 10).map((ev, i) => (
                    <div key={ev.evidence_id || i} style={{
                      padding: 10, borderRadius: 8,
                      background: 'rgba(148,163,184,0.04)',
                      border: '1px solid var(--border-subtle)',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <Badge variant={
                          ev.evidence_type === 'behavioral' ? 'emerald' :
                          ev.evidence_type === 'temporal' ? 'amber' :
                          ev.evidence_type === 'topical' ? 'indigo' :
                          ev.evidence_type === 'interaction' ? 'rose' : 'neutral'
                        }>{ev.evidence_type}</Badge>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                          {(ev.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', lineHeight: 1.4, marginBottom: 4 }}>
                        {ev.explanation || ev.evidence_id}
                      </div>
                      <LinkedChip
                        label="Open Evidence"
                        to={`/evidence?evidence_id=${ev.evidence_id}`}
                        icon={<span>📊</span>}
                      />
                    </div>
                  ))}
                </div>
              </Section>

              {/* Retrieved Memories */}
              <Section title="Retrieved Memories" icon={<span style={{ fontSize: 16 }}>📝</span>}>
                {Object.entries(data.memories?.grouped || {}).filter(([_, items]) => items.length > 0).map(([type, items]) => (
                  <div key={type} style={{ marginBottom: 12 }}>
                    <div style={{
                      fontSize: 12, fontWeight: 600, color: 'var(--text-muted)',
                      textTransform: 'capitalize', marginBottom: 6,
                    }}>{type}</div>
                    {items.slice(0, 4).map((mem, i) => (
                      <div key={mem.memory_id || i} style={{
                        padding: '6px 10px', borderRadius: 6,
                        background: 'rgba(148,163,184,0.04)', marginBottom: 4,
                        fontSize: 12, color: 'var(--text-tertiary)',
                      }}>
                        <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 2 }}>
                          <Badge variant="neutral">imp: {mem.importance_score?.toFixed(2)}</Badge>
                          {mem.similarity && <Badge variant="neutral">sim: {mem.similarity.toFixed(2)}</Badge>}
                        </div>
                        {(mem.content || '').slice(0, 120)}
                      </div>
                    ))}
                  </div>
                ))}
                {data.memories?.items?.length > 0 && (
                  <LinkedChip
                    label="View All Memories"
                    to="/memory"
                    icon={<span>📝</span>}
                  />
                )}
              </Section>

              {/* Planner Output */}
              <Section title="Planner Output" icon={<span style={{ fontSize: 16 }}>📋</span>}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  {data.planner?.intent && (
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>Intent</div>
                      <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{data.planner.intent}</div>
                    </div>
                  )}
                  {data.planner?.reasoning_mode && (
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>Reasoning Mode</div>
                      <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{data.planner.reasoning_mode}</div>
                    </div>
                  )}
                  {data.planner?.intent_confidence != null && (
                    <ConfidenceBar value={data.planner.intent_confidence} label="Intent Confidence" />
                  )}
                  {data.planner?.plan_confidence != null && (
                    <ConfidenceBar value={data.planner.plan_confidence} label="Plan Confidence" />
                  )}
                </div>
                {data.planner?.retrieval_strategy && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Retrieval Strategy</div>
                    <Badge variant="indigo">{data.planner.retrieval_strategy}</Badge>
                  </div>
                )}
                {data.planner?.selected_tools?.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Selected Tools</div>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {data.planner.selected_tools.map((t, i) => (
                        <Badge key={i}>{t}</Badge>
                      ))}
                    </div>
                  </div>
                )}
              </Section>

              {/* Decision Engine */}
              <Section title="Decision Engine" icon={<span style={{ fontSize: 16 }}>⚖️</span>}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {data.decision?.aggregate_confidence != null && (
                    <ConfidenceBar value={data.decision.aggregate_confidence} label="Aggregate Confidence" />
                  )}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                    {data.decision?.input_facts != null && (
                      <div style={{ textAlign: 'center', padding: 8, borderRadius: 8, background: 'rgba(99,102,241,0.08)' }}>
                        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--indigo-400)' }}>{data.decision.input_facts}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Input Facts</div>
                      </div>
                    )}
                    {data.decision?.output_facts != null && (
                      <div style={{ textAlign: 'center', padding: 8, borderRadius: 8, background: 'rgba(16,185,129,0.08)' }}>
                        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--emerald-400)' }}>{data.decision.output_facts}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Output Facts</div>
                      </div>
                    )}
                    {data.decision?.conflicts != null && (
                      <div style={{ textAlign: 'center', padding: 8, borderRadius: 8, background: 'rgba(244,63,94,0.08)' }}>
                        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--rose-400)' }}>{data.decision.conflicts}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Conflicts</div>
                      </div>
                    )}
                  </div>
                </div>
              </Section>

              {/* Context Builder */}
              <Section title="Context Builder" icon={<span style={{ fontSize: 16 }}>🔗</span>}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                  <div style={{ textAlign: 'center', padding: 8, borderRadius: 8, background: 'rgba(148,163,184,0.08)' }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-secondary)' }}>
                      {data.context?.context_build_ms ? `${Math.round(data.context.context_build_ms)}ms` : '--'}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Build Time</div>
                  </div>
                  <div style={{ textAlign: 'center', padding: 8, borderRadius: 8, background: 'rgba(148,163,184,0.08)' }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-secondary)' }}>
                      {data.context?.retrieved_count ?? '--'}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Retrieved</div>
                  </div>
                  <div style={{ textAlign: 'center', padding: 8, borderRadius: 8, background: 'rgba(148,163,184,0.08)' }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-secondary)' }}>
                      {data.context?.token_count ?? '--'}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Tokens</div>
                  </div>
                </div>
              </Section>

              {/* LLM Verbalizer */}
              <Section title="LLM Verbalizer" icon={<span style={{ fontSize: 16 }}>🤖</span>}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>Provider</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{data.llm?.provider || '--'}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>Model</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{data.llm?.model || '--'}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>Latency</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{data.llm?.latency_ms ? `${Math.round(data.llm.latency_ms)}ms` : '--'}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>Tokens</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{data.llm?.tokens ?? '--'}</div>
                  </div>
                </div>
              </Section>

              {/* Pipeline Trace */}
              <Section title="Pipeline Trace" icon={<span style={{ fontSize: 16 }}>⚡</span>}>
                <div style={{ marginBottom: 12 }}>
                  <TimelineBar data={data.pipeline?.timeline_ms || {}} />
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
                  {data.pipeline?.timeline_ms && Object.entries(data.pipeline.timeline_ms)
                    .filter(([k]) => k !== 'total')
                    .map(([key, val]) => val > 0 && (
                      <Badge key={key} variant="neutral">
                        {key}: {Math.round(val)}ms
                      </Badge>
                    ))}
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  <Badge variant="indigo">{data.pipeline?.inference_count || 0} inferences</Badge>
                  <Badge variant="emerald">{data.pipeline?.evidence_count || 0} evidence</Badge>
                  <Badge variant="violet">{data.pipeline?.reflection_count || 0} reflections</Badge>
                  <Badge variant="amber">{data.pipeline?.retrieved_count || 0} retrieved</Badge>
                </div>
                {data.pipeline?.errors?.length > 0 && (
                  <div style={{ marginTop: 8, padding: 8, borderRadius: 6, background: 'rgba(244,63,94,0.1)', fontSize: 12, color: 'var(--rose-400)' }}>
                    {data.pipeline.errors.map((e, i) => <div key={i}>⚠ {typeof e === 'string' ? e : e.message || JSON.stringify(e)}</div>)}
                  </div>
                )}
                <div style={{ marginTop: 8 }}>
                  <LinkedChip
                    label="View Pipeline Detail"
                    to={`/pipeline?trace=${data.trace_id}`}
                    icon={<span>⚡</span>}
                  />
                </div>
              </Section>
            </>
          )}

          {data?.error && (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--rose-400)' }}>
              <div style={{ fontSize: 32, marginBottom: 16 }}>🚫</div>
              <div>Trace not found</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

