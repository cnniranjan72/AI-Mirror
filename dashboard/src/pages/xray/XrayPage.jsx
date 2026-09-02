import { useState, useEffect } from 'react'
import { api } from '../../api/client'
import { useApi } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'
import Reveal from '../../components/motion/Reveal'
import { useReducedMotion } from '../../hooks/useMotion'

/**
 * Reasoning X-Ray — one answer, opened up.
 *
 * The architecture's central claim is that a language model decides nothing:
 * seven deterministic stages choose what to say, and the model receives a
 * finished plan to put into words. That is easy to assert and hard to believe,
 * and until now there was no way for anyone to check it.
 *
 * Every run already recorded what is needed. The bars below are real timings
 * from a real answer, and the gap between them is the argument: on a typical
 * run the six deciding stages finish in about three milliseconds while
 * verbalization takes eleven seconds.
 *
 * Bars are logarithmic. Deciding and talking differ by three or four orders of
 * magnitude, so a linear scale renders every deterministic stage as an
 * invisible sliver — which would hide the very thing the view exists to show.
 * The exact figure is printed beside each bar so the scale cannot mislead.
 */

function logWidth(ms, max) {
  if (!ms || ms <= 0) return 1.5
  // +1 keeps sub-millisecond values on the chart instead of going negative.
  return Math.max(1.5, (Math.log10(ms + 1) / Math.log10(max + 1)) * 100)
}

function fmt(ms) {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)} s`
  if (ms >= 1) return `${ms.toFixed(2)} ms`
  return `${ms.toFixed(3)} ms`
}

export default function XrayPage() {
  const { data: traces, loading: listLoading } = useApi(() => api.getTraces(undefined, 15), [])
  const [traceId, setTraceId] = useState(null)
  const reduced = useReducedMotion()

  const list = Array.isArray(traces) ? traces : []
  useEffect(() => {
    if (!traceId && list.length) setTraceId(list[0].trace_id)
  }, [list, traceId])

  const { data, loading, error, refetch } = useApi(
    () => (traceId ? api.getReasoningXray(traceId) : Promise.resolve(null)),
    [traceId],
  )

  const stages = data?.stages || []
  const maxMs = Math.max(1, ...stages.map(s => s.ms))
  const t = data?.timing

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
          Reasoning X-Ray
        </h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15, maxWidth: 740 }}>
          One answer, opened up. Every stage that ran, how long it took, how many
          candidate facts survived it, and which single stage a language model was
          allowed anywhere near.
        </p>
      </div>

      {list.length > 1 && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 18 }}>
          {list.slice(0, 8).map(tr => (
            <button
              key={tr.trace_id}
              onClick={() => setTraceId(tr.trace_id)}
              style={{
                padding: '5px 11px', borderRadius: 8, fontSize: 12, cursor: 'pointer',
                maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                border: `1px solid ${tr.trace_id === traceId ? 'rgba(99,102,241,0.5)' : 'var(--border-subtle)'}`,
                background: tr.trace_id === traceId ? 'rgba(99,102,241,0.15)' : 'transparent',
                color: tr.trace_id === traceId ? '#a5b4fc' : 'var(--text-tertiary)',
              }}
            >
              {tr.query || tr.trace_id.slice(0, 8)}
            </button>
          ))}
        </div>
      )}

      <AsyncState loading={loading || listLoading} error={error} onRetry={refetch}>
        {!data ? (
          <GlassCard gradient>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
              No reasoning runs recorded yet. Ask the twin something and it will appear here.
            </p>
          </GlassCard>
        ) : (
          <>
            <Reveal>
              <GlassCard gradient style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 3 }}>answering</div>
                <div style={{ fontSize: 19, fontWeight: 700, marginBottom: 16 }}>
                  &ldquo;{data.query}&rdquo;
                </div>

                {t?.ratio && (
                  <div style={{
                    display: 'flex', gap: 26, flexWrap: 'wrap', alignItems: 'baseline',
                    padding: '14px 16px', borderRadius: 12, marginBottom: 6,
                    background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)',
                  }}>
                    <div>
                      <div style={{ fontSize: 26, fontWeight: 800, color: '#a5b4fc' }}>{fmt(t.deciding_ms)}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>deciding what to say</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-secondary)' }}>{fmt(t.talking_ms)}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>putting it into words</div>
                    </div>
                    <div style={{ flex: '1 1 200px', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                      Talking took <strong style={{ color: '#a5b4fc' }}>{t.ratio.toLocaleString()}&times;</strong>{' '}
                      longer than every decision combined.
                    </div>
                  </div>
                )}
              </GlassCard>
            </Reveal>

            <Reveal delay={0.05}>
              <GlassCard style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>Stages</h3>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 18 }}>
                  Logarithmic — the stages differ by thousands of times, and a linear scale
                  would render every deterministic one as an invisible sliver.
                </p>

                {stages.map((s, i) => {
                  const isLLM = s.kind === 'language_model'
                  return (
                    <div key={s.name} style={{ marginBottom: 14 }}>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 13, fontWeight: 700, minWidth: 106 }}>{s.name}</span>
                        {isLLM ? (
                          <Badge variant={data.llm_called ? 'amber' : 'slate'}>
                            {data.llm_called ? 'language model' : 'no model called'}
                          </Badge>
                        ) : (
                          <Badge variant="emerald">deterministic</Badge>
                        )}
                        <span style={{ marginLeft: 'auto', fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
                          {fmt(s.ms)}
                        </span>
                      </div>
                      <div style={{ height: 9, borderRadius: 5, background: 'rgba(148,163,184,0.10)', overflow: 'hidden' }}>
                        <div style={{
                          width: `${logWidth(s.ms, maxMs)}%`, height: '100%', borderRadius: 5,
                          background: isLLM
                            ? 'linear-gradient(90deg, rgba(251,191,36,0.6), rgba(251,191,36,0.28))'
                            : 'linear-gradient(90deg, rgba(16,185,129,0.65), rgba(16,185,129,0.3))',
                          transition: reduced ? 'none' : `width 700ms cubic-bezier(0.16,1,0.3,1) ${i * 60}ms`,
                        }} />
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                        {s.detail ? <strong style={{ color: 'var(--text-tertiary)' }}>{s.detail}</strong> : null}
                        {s.detail ? ' — ' : ''}{s.purpose}
                      </div>
                    </div>
                  )
                })}
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 14, lineHeight: 1.6 }}>
                  {data.note}
                </p>
              </GlassCard>
            </Reveal>

            <Reveal delay={0.1}>
              <GlassCard>
                <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>What survived</h3>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
                  Candidate facts are dropped before the language model sees anything, so it
                  cannot reintroduce what the decision stage rejected.
                </p>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', marginBottom: 14 }}>
                  {[
                    ['retrieved', data.funnel.retrieved],
                    ['candidates', data.funnel.candidates],
                    ['into decision', data.funnel.into_decision],
                    ['kept', data.funnel.kept],
                    ['cited', data.funnel.citations],
                  ].map(([label, value], i, arr) => (
                    <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 22, fontWeight: 800, color: '#a5b4fc' }}>{value}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</div>
                      </div>
                      {i < arr.length - 1 && <span style={{ color: 'var(--text-muted)' }}>&rarr;</span>}
                    </div>
                  ))}
                </div>
                {data.funnel.dropped_total > 0 ? (
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                    Dropped:{' '}
                    {Object.entries(data.funnel.dropped).map(([reason, n], i, a) => (
                      <span key={reason}>
                        <strong>{n}</strong> for {reason}{i < a.length - 1 ? ', ' : ''}
                      </span>
                    ))}
                    .
                  </div>
                ) : (
                  <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                    Nothing was dropped on this run — every candidate cleared the threshold.
                  </div>
                )}
              </GlassCard>
            </Reveal>
          </>
        )}
      </AsyncState>
    </div>
  )
}
