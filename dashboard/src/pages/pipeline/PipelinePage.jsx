import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTraces } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import LoadingSkeleton from '../../components/ui/LoadingSkeleton'
import PipelineStage from '../../components/pipeline/PipelineStage'
import { RefreshIcon } from '../../icons/icons'
import ExplainabilityPanel from '../../components/explain/ExplainabilityPanel'

// A query trace records the QUERY pipeline (not the ingest pipeline), so show
// exactly those stages with their real per-stage timings.
const pipelineStages = [
  'Runtime', 'Planner', 'Retriever', 'Fusion', 'Decision', 'Context', 'LLM',
]

export default function PipelinePage() {
  const navigate = useNavigate()
  const { data: traces, loading, refetch } = useTraces()
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [selectedTrace, setSelectedTrace] = useState(null)
  const [selectedStage, setSelectedStage] = useState(null)
  const [explainTrace, setExplainTrace] = useState(null)

  const traceList = Array.isArray(traces) ? traces : (traces?.traces || [])
  const activeTrace = selectedTrace
    ? traceList.find(t => t.trace_id === selectedTrace)
    : traceList[0]

  // Derive stage latencies from the active trace
  const getStageLatency = (stage) => {
    if (!activeTrace) return undefined
    const mapping = {
      'Runtime': activeTrace.runtime_load_ms,
      'Planner': activeTrace.planning_ms,
      'Retriever': activeTrace.retrieval_ms,
      'Fusion': activeTrace.fusion_ms,
      'Decision': activeTrace.decision_ms,
      'Context': activeTrace.context_build_ms,
      'LLM': activeTrace.verbalization_ms,
    }
    return mapping[stage]
  }

  // Determine stage status
  const getStageStatus = (stage, idx) => {
    if (!activeTrace) return 'idle'
    if (activeTrace.success === false && idx >= pipelineStages.length - 1) return 'error'
    const latency = getStageLatency(stage)
    if (activeTrace.success && latency > 0) return 'success'
    if (activeTrace.success === false) return 'error'
    if (latency > 0) return 'success'
    return 'idle'
  }

  const totalMs = activeTrace?.total_ms || 0

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Pipeline</h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Animated cognitive processing pipeline</p>
      </div>

      <div style={{ display: 'flex', gap: 16, marginBottom: 24, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 200 }}>
          <select
            value={selectedTrace || ''}
            onChange={e => setSelectedTrace(e.target.value || null)}
            style={{
              width: '100%', padding: '10px 12px', borderRadius: 8,
              background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
              color: 'var(--text-primary)', fontSize: 13, outline: 'none',
            }}
          >
            <option value="">Latest trace</option>
            {traceList.map(t => (
              <option key={t.trace_id} value={t.trace_id}>
                {(t.query || 'Query').slice(0, 50)} — {t.total_ms ? `${Math.round(t.total_ms)}ms` : '--'}
              </option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => setAutoRefresh(!autoRefresh)} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8,
            border: `1px solid ${autoRefresh ? 'rgba(99,102,241,0.3)' : 'var(--border-subtle)'}`,
            background: autoRefresh ? 'rgba(99,102,241,0.1)' : 'transparent',
            color: autoRefresh ? 'var(--indigo-400)' : 'var(--text-tertiary)',
            fontSize: 13, cursor: 'pointer', fontWeight: 500,
          }}>
            <div style={{ animation: autoRefresh ? 'spin 2s linear infinite' : 'none' }}><RefreshIcon /></div>
            Auto
          </button>
          <button onClick={refetch} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8,
            border: '1px solid var(--border-subtle)', background: 'transparent',
            color: 'var(--text-tertiary)', fontSize: 13, cursor: 'pointer', fontWeight: 500,
          }}>
            <RefreshIcon /> Refresh
          </button>
        </div>
      </div>

      {/* Pipeline Summary */}
      {activeTrace && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 12, marginBottom: 24 }}>
          <GlassCard padding="md">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: totalMs > 1000 ? 'var(--amber-400)' : 'var(--emerald-400)' }}>
                {totalMs > 0 ? `${Math.round(totalMs)}ms` : '--'}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Total Latency</div>
            </div>
          </GlassCard>
          <GlassCard padding="md">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: activeTrace.success ? 'var(--emerald-400)' : 'var(--rose-400)' }}>
                {activeTrace.success ? 'Success' : 'Failed'}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Status</div>
            </div>
          </GlassCard>
          <GlassCard padding="md">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--indigo-400)' }}>{activeTrace.inference_count || 0}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Inferences</div>
            </div>
          </GlassCard>
          <GlassCard padding="md">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--violet-400)' }}>{activeTrace.evidence_count || 0}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Evidence</div>
            </div>
          </GlassCard>
          <GlassCard padding="md">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--pink-400)' }}>{activeTrace.token_count || 0}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Tokens</div>
            </div>
          </GlassCard>
          <GlassCard padding="md">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--cyan-400)' }}>{activeTrace.retrieved_count || 0}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Retrieved</div>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Pipeline Stages */}
      {activeTrace && (
        <GlassCard gradient padding="2xl">
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: 16, fontWeight: 600 }}>Pipeline Execution</h3>
              {activeTrace.trace_id && <Badge variant="neutral">Trace: {activeTrace.trace_id.slice(0, 12)}</Badge>}
            </div>
            {activeTrace.query && (
              <div style={{ fontSize: 13, color: 'var(--text-tertiary)', marginTop: 8, padding: '8px 12px', borderRadius: 6, background: 'rgba(0,0,0,0.2)' }}>
                Query: {activeTrace.query}
              </div>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {pipelineStages.map((stage, i) => (
              <div
                key={stage}
                onClick={() => setSelectedStage(selectedStage === stage ? null : stage)}
                style={{ cursor: 'pointer' }}
              >
                <PipelineStage
                  name={stage}
                  index={i}
                  status={getStageStatus(stage, i)}
                  latency={getStageLatency(stage)}
                  error={i === pipelineStages.length - 1 && activeTrace.success === false ? activeTrace.errors?.[0] : undefined}
                  output={undefined}
                />
                {selectedStage === stage && (
                  <div style={{
                    margin: '4px 0 8px 32px', padding: 12, borderRadius: 8,
                    background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-subtle)',
                    animation: 'fadeIn 0.2s ease-out both',
                  }}>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
                      Stage Detail: <span style={{ color: 'var(--text-secondary)' }}>{stage}</span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                      <div>
                        <div style={{ color: 'var(--text-muted)' }}>Input</div>
                        <div style={{ color: 'var(--text-secondary)' }}>{activeTrace?.query || '(pipeline input)'}</div>
                      </div>
                      <div>
                        <div style={{ color: 'var(--text-muted)' }}>Latency</div>
                        <div style={{ color: 'var(--text-secondary)' }}>{getStageLatency(stage) ? `${Math.round(getStageLatency(stage))}ms` : '--'}</div>
                      </div>
                      <div>
                        <div style={{ color: 'var(--text-muted)' }}>Status</div>
                        <Badge variant={
                          getStageStatus(stage, i) === 'success' ? 'emerald' :
                          getStageStatus(stage, i) === 'error' ? 'danger' : 'neutral'
                        }>{getStageStatus(stage, i)}</Badge>
                      </div>
                      <div>
                        <div style={{ color: 'var(--text-muted)' }}>Evidence Gen.</div>
                        <div style={{ color: 'var(--text-secondary)' }}>{activeTrace?.evidence_count || 0}</div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                      <button onClick={(e) => { e.stopPropagation(); navigate(`/trace/${activeTrace?.trace_id}`) }}
                        style={{ padding: '4px 10px', borderRadius: 6, fontSize: 11, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', color: 'var(--indigo-400)', cursor: 'pointer' }}>
                        View Full Trace →
                      </button>
                      <button onClick={(e) => { e.stopPropagation(); setExplainTrace(activeTrace?.trace_id) }}
                        style={{ padding: '4px 10px', borderRadius: 6, fontSize: 11, background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)', color: 'var(--emerald-400)', cursor: 'pointer' }}>
                        🔍 Explain
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {!activeTrace && (
        <GlassCard>
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
            <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.3 }}>⚡</div>
            <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>No Pipeline Data</div>
            <div style={{ fontSize: 14 }}>Ingest behavioral data to see pipeline execution traces</div>
          </div>
        </GlassCard>
      )}

      {explainTrace && (
        <ExplainabilityPanel traceId={explainTrace} onClose={() => setExplainTrace(null)} />
      )}
    </div>
  )
}
