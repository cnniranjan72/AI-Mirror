import { useState } from 'react'
import { useBehaviorObjects, useApi } from '../../hooks/useApi'
import { api } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#10b981', '#f59e0b', '#06b6d4', '#a78bfa', '#f472b6']

export default function BehaviorPage() {
  const { data: behaviorObjects, loading } = useBehaviorObjects()
  const { data: sessions } = useApi(() => api.getSessions())
  const [filter, setFilter] = useState('all')

  const objects = Array.isArray(behaviorObjects) ? behaviorObjects : (behaviorObjects?.objects || [])
  const eventsList = sessions ? sessions.flatMap(s => s.events || []) : []

  const filtered = filter === 'all' ? objects : objects.filter(o => o.behavior_type === filter || o.type === filter)

  const typeCounts = objects.reduce((acc, o) => {
    const t = o.behavior_type || o.type || 'unknown'
    acc[t] = (acc[t] || 0) + 1
    return acc
  }, {})

  const chartData = Object.entries(typeCounts).map(([name, count]) => ({ name, count }))

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Behavior</h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Interactive behavior timeline and cluster analysis</p>
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 24, alignItems: 'center', flexWrap: 'wrap' }}>
        <Badge variant="indigo">{objects.length} behavior objects</Badge>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {['all', ...Object.keys(typeCounts)].map(t => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              style={{
                padding: '4px 12px', borderRadius: 100, border: '1px solid var(--border-subtle)',
                background: filter === t ? 'rgba(99,102,241,0.15)' : 'transparent',
                color: filter === t ? 'var(--indigo-400)' : 'var(--text-tertiary)',
                fontSize: 12, fontWeight: 500, cursor: 'pointer',
                textTransform: 'capitalize',
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
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Behavior Type Distribution</h3>
            <Badge variant="neutral">Clusters</Badge>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} width={100} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Timeline</h3>
            <Badge variant="neutral">Recent events</Badge>
          </div>
          <div style={{ maxHeight: 300, overflow: 'auto' }}>
            {eventsList.length === 0 && (
              <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>No events recorded</div>
            )}
            {eventsList.slice(0, 20).map((evt, i) => (
              <div key={evt.id || i} style={{
                display: 'flex', gap: 12, padding: '8px 0',
                borderBottom: '1px solid var(--border-subtle)',
                animation: `fadeIn 0.3s ease-out ${i * 0.03}s both`,
              }}>
                <div style={{ width: 24, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i % COLORS.length], flexShrink: 0 }} />
                  {i < eventsList.length - 1 && <div style={{ width: 1, flex: 1, background: 'var(--border-subtle)', marginTop: 4 }} />}
                </div>
                <div style={{ flex: 1, paddingBottom: 4 }}>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500 }}>{evt.caption || evt.username || `Event ${i + 1}`}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                    {evt.username && `@${evt.username} · `}{evt.watch_time ? `${Math.round(evt.watch_time)}s` : ''}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      <GlassCard gradient>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Behavior Objects</h3>
          <Badge variant="neutral">{filtered.length} items</Badge>
        </div>
        {filtered.length === 0 ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>No behavior objects found</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="table" style={{ minWidth: 600 }}>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Label</th>
                  <th>Confidence</th>
                  <th>Frequency</th>
                  <th>Last Observed</th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 50).map((obj, i) => (
                  <tr key={obj.object_id || i}>
                    <td><Badge variant={['indigo', 'violet', 'pink', 'emerald'][i % 4]}>{obj.behavior_type || obj.type || '--'}</Badge></td>
                    <td style={{ fontWeight: 500 }}>{obj.label || obj.name || `Object ${i + 1}`}</td>
                    <td>{obj.confidence ? `${Math.round(obj.confidence * 100)}%` : '--'}</td>
                    <td>{obj.frequency || obj.count || '--'}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                      {obj.last_observed ? new Date(obj.last_observed).toLocaleDateString() : '--'}
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
