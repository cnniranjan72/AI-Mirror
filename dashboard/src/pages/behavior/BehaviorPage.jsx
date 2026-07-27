import { useState } from 'react'
import { useBehaviorObjects } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#10b981', '#f59e0b', '#06b6d4', '#a78bfa', '#f472b6']

const stateVariant = (s) => ({
  growing: 'emerald', stable: 'indigo', mature: 'violet',
  declining: 'amber', dormant: 'neutral',
}[s] || 'neutral')

export default function BehaviorPage() {
  const { data: behaviorObjects, loading } = useBehaviorObjects()
  const [filter, setFilter] = useState('all')

  const objects = Array.isArray(behaviorObjects) ? behaviorObjects : (behaviorObjects?.objects || [])

  const states = [...new Set(objects.map(o => o.lifecycle_state).filter(Boolean))]
  const filtered = filter === 'all' ? objects : objects.filter(o => o.lifecycle_state === filter)

  // Top topics by importance — the clearest "what this person engages with".
  const chartData = [...objects]
    .sort((a, b) => (b.importance_score || 0) - (a.importance_score || 0))
    .slice(0, 10)
    .map(o => ({ name: o.topic || o.unique_id, value: Math.round((o.importance_score || 0) * 100) }))

  // Aggregate creator frequency across all behavior objects.
  const creatorCounts = {}
  objects.forEach(o => (o.creators || []).forEach(c => { creatorCounts[c] = (creatorCounts[c] || 0) + 1 }))
  const topCreators = Object.entries(creatorCounts)
    .sort((a, b) => b[1] - a[1]).slice(0, 12)

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Behavior</h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Consolidated behavior objects and cluster analysis</p>
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 24, alignItems: 'center', flexWrap: 'wrap' }}>
        <Badge variant="indigo">{objects.length} behavior objects</Badge>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {['all', ...states].map(t => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              style={{
                padding: '4px 12px', borderRadius: 100, border: '1px solid var(--border-subtle)',
                background: filter === t ? 'rgba(99,102,241,0.15)' : 'transparent',
                color: filter === t ? 'var(--indigo-400)' : 'var(--text-tertiary)',
                fontSize: 12, fontWeight: 500, cursor: 'pointer', textTransform: 'capitalize',
              }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Top Topics by Importance</h3>
            <Badge variant="neutral">Clusters</Badge>
          </div>
          {chartData.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>No behavior objects yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} unit="%" />
                <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} width={110} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, fontSize: 12 }} labelStyle={{ color: '#e2e8f0' }} itemStyle={{ color: '#e2e8f0' }} />
                <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                  {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </GlassCard>

        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Top Creators</h3>
            <Badge variant="neutral">{Object.keys(creatorCounts).length} tracked</Badge>
          </div>
          <div style={{ maxHeight: 320, overflow: 'auto' }}>
            {topCreators.length === 0 ? (
              <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>No creators yet</div>
            ) : topCreators.map(([name, count], i) => {
              const max = topCreators[0][1] || 1
              return (
                <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '7px 0' }}>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', width: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    @{name}
                  </div>
                  <div style={{ flex: 1, height: 8, background: 'rgba(148,163,184,0.08)', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ width: `${(count / max) * 100}%`, height: '100%', background: COLORS[i % COLORS.length], borderRadius: 4 }} />
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', width: 24, textAlign: 'right' }}>{count}</div>
                </div>
              )
            })}
          </div>
        </GlassCard>
      </div>

      <GlassCard gradient>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Behavior Objects</h3>
          <Badge variant="neutral">{filtered.length} items</Badge>
        </div>
        {loading ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>Loading…</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>No behavior objects found</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="table" style={{ minWidth: 640 }}>
              <thead>
                <tr>
                  <th>Topic</th>
                  <th>Lifecycle</th>
                  <th>Confidence</th>
                  <th>Importance</th>
                  <th>Creators</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {[...filtered]
                  .sort((a, b) => (b.importance_score || 0) - (a.importance_score || 0))
                  .slice(0, 50).map((obj, i) => (
                  <tr key={obj.unique_id || i}>
                    <td style={{ fontWeight: 500, textTransform: 'capitalize' }}>{obj.topic || '—'}</td>
                    <td><Badge variant={stateVariant(obj.lifecycle_state)}>{obj.lifecycle_state || '—'}</Badge></td>
                    <td>{obj.confidence_score != null ? `${Math.round(obj.confidence_score * 100)}%` : '—'}</td>
                    <td>{obj.importance_score != null ? `${Math.round(obj.importance_score * 100)}%` : '—'}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>{(obj.creators || []).length}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                      {obj.updated_at ? new Date(obj.updated_at).toLocaleDateString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  )
}
