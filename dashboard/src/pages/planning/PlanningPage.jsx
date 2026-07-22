import { useTraces } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import { LayersIcon, CpuIcon, TargetIcon, ZapIcon, NetworkIcon } from '../../icons/icons'

const stageNames = ['intent', 'retrieval', 'reasoning', 'response']

export default function PlanningPage() {
  const { data: traces, loading } = useTraces()
  const traceList = Array.isArray(traces) ? traces : (traces?.traces || [])

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Planning</h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Cognitive planner output and execution flow</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16, marginBottom: 32 }}>
        <GlassCard>
          <div style={{ textAlign: 'center', padding: '16px 0' }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#818cf8', margin: '0 auto 12px' }}>
              <TargetIcon />
            </div>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#818cf8' }}>{traceList.filter(t => t.intent_type).length}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Intent Plans</div>
          </div>
        </GlassCard>
        <GlassCard>
          <div style={{ textAlign: 'center', padding: '16px 0' }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#a78bfa', margin: '0 auto 12px' }}>
              <LayersIcon />
            </div>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#a78bfa' }}>{traceList.filter(t => t.reasoning_mode).length}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Reasoning Plans</div>
          </div>
        </GlassCard>
        <GlassCard>
          <div style={{ textAlign: 'center', padding: '16px 0' }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#34d399', margin: '0 auto 12px' }}>
              <NetworkIcon />
            </div>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#34d399' }}>{traceList.filter(t => t.retrieved_count > 0).length}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Retrieval Plans</div>
          </div>
        </GlassCard>
      </div>

      <GlassCard gradient>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Execution Flow</h3>
          <Badge variant="neutral">{traceList.length} traces</Badge>
        </div>
        {traceList.length === 0 ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>No execution traces available</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {traceList.slice(0, 10).map((t, i) => (
              <div key={t.trace_id || i} style={{
                padding: '16px', borderRadius: 8,
                background: 'rgba(148,163,184,0.04)', border: '1px solid var(--border-subtle)',
                animation: `fadeIn 0.3s ease-out ${i * 0.05}s both`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Badge variant={t.success ? 'emerald' : 'danger'} dot>{t.success ? 'Success' : 'Failed'}</Badge>
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>{t.query || 'Query'}</span>
                  </div>
                  <Badge variant="neutral">{t.total_ms ? `${Math.round(t.total_ms)}ms` : '--'}</Badge>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                  {stageNames.map(stage => {
                    const val = t[`${stage}_ms`]
                    const maxVal = Math.max(t.planning_ms || 0, t.retrieval_ms || 0, t.fusion_ms || 0, t.verbalization_ms || 0, 1)
                    const pct = val ? (val / maxVal) * 100 : 0
                    return (
                      <div key={stage}>
                        <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'capitalize', marginBottom: 4 }}>{stage}</div>
                        <div style={{ height: 4, borderRadius: 2, background: 'rgba(148,163,184,0.1)', overflow: 'hidden' }}>
                          <div style={{ width: `${pct}%`, height: '100%', borderRadius: 2, background: 'var(--accent-gradient)', transition: 'width 0.5s ease' }} />
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 2 }}>{val ? `${Math.round(val)}ms` : '--'}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  )
}
