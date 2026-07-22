import { useParams, Link } from 'react-router-dom'
import { useTraceDetail } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import LoadingSkeleton from '../../components/ui/LoadingSkeleton'
import { ChevronLeftIcon, CopyIcon } from '../../icons/icons'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const stageColors = {
  runtime_load_ms: '#6366f1', planning_ms: '#8b5cf6', retrieval_ms: '#ec4899',
  ranking_ms: '#f59e0b', fusion_ms: '#10b981', decision_ms: '#06b6d4',
  context_build_ms: '#a78bfa', verbalization_ms: '#f472b6',
}

export default function TracePage() {
  const { traceId } = useParams()
  const { data: trace, loading, error } = useTraceDetail(traceId)

  if (loading) return <LoadingSkeleton type="card" count={4} />
  if (error) return <div style={{ padding: 32, color: '#f87171' }}>Error: {error}</div>
  if (!trace) return <div style={{ padding: 32, color: 'var(--text-muted)' }}>Trace not found</div>

  const stages = [
    { name: 'Runtime Load', key: 'runtime_load_ms', value: trace.runtime_load_ms || 0 },
    { name: 'Planning', key: 'planning_ms', value: trace.planning_ms || 0 },
    { name: 'Retrieval', key: 'retrieval_ms', value: trace.retrieval_ms || 0 },
    { name: 'Ranking', key: 'ranking_ms', value: trace.ranking_ms || 0 },
    { name: 'Fusion', key: 'fusion_ms', value: trace.fusion_ms || 0 },
    { name: 'Decision', key: 'decision_ms', value: trace.decision_ms || 0 },
    { name: 'Context', key: 'context_build_ms', value: trace.context_build_ms || 0 },
    { name: 'Verbalization', key: 'verbalization_ms', value: trace.verbalization_ms || 0 },
  ]

  const totalMs = stages.reduce((s, st) => s + st.value, 0)

  return (
    <div>
      <Link to="/pipeline" style={{
        display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--text-tertiary)',
        fontSize: 13, textDecoration: 'none', marginBottom: 24,
      }}>
        <ChevronLeftIcon /> Back to Pipeline
      </Link>

      <div style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <h1 className="gradient-text" style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.03em' }}>Execution Trace</h1>
          <Badge variant={trace.success ? 'emerald' : 'danger'} dot>{trace.success ? 'Success' : 'Failed'}</Badge>
        </div>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 14 }}>
          ID: {trace.trace_id}
        </p>
      </div>

      {/* Query */}
      {trace.query && (
        <GlassCard style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>Query</div>
          <div style={{ fontSize: 15, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{trace.query}</div>
        </GlassCard>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        {/* Timing breakdown */}
        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Stage Timing</h3>
            <Badge variant="neutral">{totalMs > 0 ? `${Math.round(totalMs)}ms total` : '--'}</Badge>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stages} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} unit="ms" />
              <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} width={100} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {stages.map((s) => <Cell key={s.key} fill={stageColors[s.key] || '#6366f1'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>

        {/* Stats */}
        <GlassCard gradient>
          <div style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Trace Details</h3>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[
              ['Intent', trace.intent_type, 'indigo'],
              ['Reasoning', trace.reasoning_mode, 'violet'],
              ['Confidence', trace.aggregate_confidence ? `${Math.round(trace.aggregate_confidence * 100)}%` : '--', 'emerald'],
              ['Inferences', trace.inference_count, 'pink'],
              ['Reflections', trace.reflection_count, 'rose'],
              ['Behavior Objects', trace.behavior_object_count, 'amber'],
              ['Evidence', trace.evidence_count, 'cyan'],
              ['Retrieved', trace.retrieved_count, 'indigo'],
              ['Facts In', trace.decision_input_facts, 'violet'],
              ['Facts Out', trace.decision_output_facts, 'emerald'],
              ['Conflicts', trace.decision_conflicts, 'rose'],
              ['Tokens', trace.token_count, 'amber'],
            ].map(([label, value, accent]) => (
              <div key={label} style={{ padding: '10px 12px', borderRadius: 8, background: 'rgba(148,163,184,0.04)' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: `var(--${accent}-400)` }}>{value ?? '--'}</div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* Error information */}
      {trace.errors && trace.errors.length > 0 && (
        <GlassCard style={{ marginBottom: 24 }}>
          <div style={{ color: '#f87171', fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Errors</div>
          {trace.errors.map((err, i) => (
            <div key={i} style={{ padding: '8px 12px', borderRadius: 6, background: 'rgba(239,68,68,0.08)', marginBottom: 4, fontSize: 13, fontFamily: 'var(--font-mono)' }}>
              {err}
            </div>
          ))}
        </GlassCard>
      )}

      {/* Raw trace data */}
      <GlassCard>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600 }}>Raw Trace Data</h3>
          <button onClick={() => navigator.clipboard.writeText(JSON.stringify(trace, null, 2))} style={{
            display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px',
            borderRadius: 6, border: '1px solid var(--border-subtle)',
            background: 'transparent', color: 'var(--text-muted)', fontSize: 12, cursor: 'pointer',
          }}>
            <CopyIcon /> Copy
          </button>
        </div>
        <pre style={{
          background: 'rgba(0,0,0,0.3)', borderRadius: 8, padding: 16,
          fontSize: 11, lineHeight: 1.6, overflow: 'auto', maxHeight: 400,
          color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)',
        }}>
          {JSON.stringify(trace, null, 2)}
        </pre>
      </GlassCard>
    </div>
  )
}
