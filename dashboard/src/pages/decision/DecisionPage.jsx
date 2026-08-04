import { useState } from 'react'
import { useTraces } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import StatCard from '../../components/ui/StatCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'
import { BrainIcon, TargetIcon, CheckIcon, LayersIcon, AlertIcon } from '../../icons/icons'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import ExplainabilityPanel from '../../components/explain/ExplainabilityPanel'
import DecisionTree from '../../components/decision/DecisionTree'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'

const COLORS = ['#10b981', '#f59e0b', '#ef4444', '#6366f1', '#8b5cf6']

export default function DecisionPage() {
  const { data: traces, loading, error, refetch } = useTraces()
  const [explainTrace, setExplainTrace] = useState(null)
  const [treeTrace, setTreeTrace] = useState(null)

  const traceList = Array.isArray(traces) ? traces : (traces?.traces || [])
  const decisions = traceList.filter(t => t.decision_input_facts > 0 || t.decision_output_facts > 0)

  const totalInput = decisions.reduce((s, d) => s + (d.decision_input_facts || 0), 0)
  const totalOutput = decisions.reduce((s, d) => s + (d.decision_output_facts || 0), 0)
  const totalConflicts = decisions.reduce((s, d) => s + (d.decision_conflicts || 0), 0)
  const avgConfidence = decisions.length
    ? decisions.reduce((s, d) => s + (d.aggregate_confidence || 0), 0) / decisions.length
    : 0

  const chartData = decisions.slice(-10).reverse().map((d, i) => ({
    name: `#${i + 1}`,
    Input: d.decision_input_facts || 0,
    Output: d.decision_output_facts || 0,
    Conflicts: d.decision_conflicts || 0,
  }))

  const confidenceData = decisions.slice(-10).reverse().map((d, i) => ({
    name: `#${i + 1}`,
    confidence: d.aggregate_confidence || 0,
  }))

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 32 }}>
        <div style={{ width: 68, height: 68, flexShrink: 0, margin: '-8px 0' }}>
          <CharacterCreature3D size={68} variant="scale" confidence={avgConfidence || 0.4} thinking={loading} showLabels={false} />
        </div>
        <div>
          <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Decision</h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Cognitive decision-making analysis</p>
        </div>
      </div>

      <AsyncState loading={loading} error={error} onRetry={refetch}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, marginBottom: 32 }}>
        <StatCard label="Decisions" value={decisions.length} icon={BrainIcon} accent="indigo" loading={loading} />
        <StatCard label="Facts Input" value={totalInput} icon={LayersIcon} accent="violet" loading={loading} />
        <StatCard label="Facts Output" value={totalOutput} icon={CheckIcon} accent="emerald" loading={loading} />
        <StatCard label="Conflicts" value={totalConflicts} icon={AlertIcon} accent="rose" loading={loading} />
        <StatCard label="Avg Confidence" value={avgConfidence ? `${Math.round(avgConfidence * 100)}%` : '--'} icon={TargetIcon} accent="amber" loading={loading} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Decision Facts</h3>
            <Badge variant="neutral">Input vs Output</Badge>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, fontSize: 12 }} labelStyle={{ color: '#e2e8f0' }} itemStyle={{ color: '#e2e8f0' }} />
              <Bar dataKey="Input" fill="#6366f1" radius={[2, 2, 0, 0]} />
              <Bar dataKey="Output" fill="#10b981" radius={[2, 2, 0, 0]} />
              <Bar dataKey="Conflicts" fill="#f43f5e" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Decision Confidence</h3>
            <Badge variant="neutral">Per decision</Badge>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={confidenceData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 1]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, fontSize: 12 }} labelStyle={{ color: '#e2e8f0' }} itemStyle={{ color: '#e2e8f0' }} />
              <Bar dataKey="confidence" radius={[4, 4, 0, 0]}>
                {confidenceData.map((_, i) => (
                  <Cell key={i} fill={confidenceData[i]?.confidence > 0.7 ? '#10b981' : confidenceData[i]?.confidence > 0.4 ? '#f59e0b' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>
      </div>

      <GlassCard gradient>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>
            {treeTrace ? 'Decision Tree' : 'Decision Log'}
          </h3>
          <div style={{ display: 'flex', gap: 4 }}>
            {treeTrace && (
              <button onClick={() => setTreeTrace(null)} style={{
                padding: '6px 12px', borderRadius: 6, border: '1px solid var(--border-subtle)',
                background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12,
              }}>
                ← Back to Log
              </button>
            )}
            <Badge variant="neutral">{decisions.length} total</Badge>
          </div>
        </div>

        {treeTrace ? (
          <DecisionTree traceId={treeTrace} onExplain={setExplainTrace} />
        ) : decisions.length === 0 ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>No decisions recorded</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {decisions.slice(-10).reverse().map((d, i) => (
              <div
                key={d.trace_id || i}
                onClick={() => setTreeTrace(d.trace_id)}
                style={{
                  padding: '12px 16px', borderRadius: 8, cursor: 'pointer',
                  background: 'rgba(148,163,184,0.04)', border: '1px solid var(--border-subtle)',
                  animation: `fadeIn 0.3s ease-out ${i * 0.03}s both`,
                  transition: 'all 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(99,102,241,0.06)'}
                onMouseLeave={e => e.currentTarget.style.background = 'rgba(148,163,184,0.04)'}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {/* Whether the decision/fusion engine accepted facts without
                        conflict — distinct from d.success, which only means the
                        pipeline ran without throwing (a query that returns zero
                        facts, or resolves conflicts, still "succeeds" in that
                        sense but isn't a clean Approved decision). */}
                    <Badge variant={d.decision_conflicts === 0 && d.decision_output_facts > 0 ? 'emerald' : 'danger'} dot>
                      {d.decision_conflicts === 0 && d.decision_output_facts > 0 ? 'Approved' : 'Filtered/Rejected'}
                    </Badge>
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
                      {d.query?.slice(0, 60)}{(d.query || '').length > 60 ? '...' : ''}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <Badge variant={d.aggregate_confidence > 0.7 ? 'emerald' : d.aggregate_confidence > 0.4 ? 'warning' : 'danger'}>
                      {d.aggregate_confidence ? `${Math.round(d.aggregate_confidence * 100)}%` : '--'}
                    </Badge>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>🌳</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-muted)' }}>
                  <span>{d.decision_input_facts || 0} facts in</span>
                  <span>{d.decision_output_facts || 0} facts out</span>
                  <span>{d.decision_conflicts || 0} conflicts</span>
                  <span>{d.total_ms ? `${Math.round(d.total_ms)}ms` : ''}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
      </AsyncState>

      {explainTrace && (
        <ExplainabilityPanel traceId={explainTrace} onClose={() => setExplainTrace(null)} />
      )}
    </div>
  )
}
