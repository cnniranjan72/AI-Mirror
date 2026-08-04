import { useEffect, useState } from 'react'

const STAGE_COLOR = {
  Runtime: '#06b6d4', Planner: '#0ea5e9', Retriever: '#3b82f6',
  Fusion: '#6366f1', Decision: '#8b5cf6', Context: '#a78bfa', LLM: '#ec4899',
}

/**
 * A real latency waterfall — each segment's width is that stage's actual
 * share of total_ms from the trace, not a fixed/decorative split. Segments
 * animate in left-to-right with a stagger proportional to their own
 * duration, so a slow stage visibly takes longer to "fill" than a fast one.
 */
export default function PipelineWaterfall({ stages, traceKey }) {
  const [grown, setGrown] = useState(false)
  const total = stages.reduce((s, st) => s + Math.max(0, st.ms || 0), 0)

  useEffect(() => {
    setGrown(false)
    const t = requestAnimationFrame(() => requestAnimationFrame(() => setGrown(true)))
    return () => cancelAnimationFrame(t)
  }, [traceKey])

  if (total <= 0) return null

  let cumulativeMs = 0
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', height: 36, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border-subtle)', background: 'rgba(148,163,184,0.04)' }}>
        {stages.filter(s => s.ms > 0).map((s) => {
          const widthPct = (s.ms / total) * 100
          const delayMs = (cumulativeMs / total) * 900
          cumulativeMs += s.ms
          return (
            <div
              key={s.name}
              title={`${s.name}: ${Math.round(s.ms)}ms (${Math.round(widthPct)}%)`}
              style={{
                width: grown ? `${widthPct}%` : '0%',
                background: `linear-gradient(90deg, ${STAGE_COLOR[s.name] || '#818cf8'}, ${STAGE_COLOR[s.name] || '#818cf8'}cc)`,
                transition: `width 0.5s cubic-bezier(0.16,1,0.3,1) ${delayMs}ms`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                borderRight: '1px solid rgba(0,0,0,0.2)',
                minWidth: widthPct > 3 ? undefined : 0,
                overflow: 'hidden', whiteSpace: 'nowrap',
              }}
            >
              {widthPct > 8 && (
                <span style={{ fontSize: 10, fontWeight: 700, color: 'white', textShadow: '0 1px 2px rgba(0,0,0,0.4)' }}>
                  {Math.round(s.ms)}ms
                </span>
              )}
            </div>
          )
        })}
      </div>
      <div style={{ display: 'flex', gap: 14, marginTop: 8, flexWrap: 'wrap' }}>
        {stages.filter(s => s.ms > 0).map(s => (
          <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--text-muted)' }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: STAGE_COLOR[s.name] || '#818cf8', display: 'inline-block' }} />
            {s.name} · {Math.round(s.ms)}ms
          </div>
        ))}
      </div>
    </div>
  )
}
