import { useState } from 'react'
import { useCognitiveMetrics, useIdentity } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import LoadingSkeleton from '../../components/ui/LoadingSkeleton'
import {
  CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, PieChart, Pie, Cell, Legend,
  XAxis, YAxis,
} from 'recharts'

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#10b981', '#f59e0b', '#06b6d4', '#f43f5e', '#a78bfa']

const metricConfig = [
  { key: 'behavior_object_count', label: 'Behavior Objects', color: '#6366f1' },
  { key: 'evidence_count', label: 'Evidence', color: '#8b5cf6' },
  { key: 'inference_count', label: 'Inferences', color: '#ec4899' },
  { key: 'identity_confidence', label: 'Confidence', color: '#10b981' },
  { key: 'identity_version', label: 'Identity Version', color: '#f59e0b' },
]

export default function AnalyticsPage() {
  const { metrics, loading } = useCognitiveMetrics()
  const { current: identityData } = useIdentity()

  const metricList = Array.isArray(metrics) ? metrics : []
  const identity = identityData

  const groupedMetrics = metricConfig.map(mc => ({
    ...mc,
    values: metricList
      .filter(m => m.metric_name === mc.key)
      .slice(-20)
      .map((m, i) => ({
        index: i + 1,
        value: m.metric_value || 0,
        timestamp: m.recorded_at,
      })),
  }))

  const pieData = metricConfig.map(mc => ({
    name: mc.label,
    value: groupedMetrics.find(g => g.key === mc.key)?.values?.reduce((s, v) => s + v.value, 0) || 1,
  }))

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Analytics</h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Cognitive metrics and trends</p>
      </div>

      {loading ? (
        <LoadingSkeleton type="card" count={3} />
      ) : (
        <>
          {/* Metric Trends */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
            {groupedMetrics.slice(0, 4).map(mc => (
              <GlassCard key={mc.key} gradient>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 600 }}>{mc.label}</h3>
                  <Badge variant="neutral">
                    {mc.values.length > 0 ? mc.values[mc.values.length - 1].value.toFixed(2) : '--'}
                  </Badge>
                </div>
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={mc.values}>
                    <defs>
                      <linearGradient id={`grad_${mc.key}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={mc.color} stopOpacity={0.2} />
                        <stop offset="95%" stopColor={mc.color} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
                    <XAxis dataKey="index" tick={false} axisLine={false} />
                    <YAxis tick={false} axisLine={false} />
                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, fontSize: 12 }} />
                    <Area type="monotone" dataKey="value" stroke={mc.color} fill={`url(#grad_${mc.key})`} strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </GlassCard>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
            {/* Distribution */}
            <GlassCard gradient>
              <div style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 16, fontWeight: 600 }}>Metric Distribution</h3>
              </div>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" outerRadius={100} innerRadius={50} paddingAngle={3} dataKey="value">
                    {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, fontSize: 12 }} />
                  <Legend formatter={(value) => <span style={{ color: '#94a3b8', fontSize: 12 }}>{value}</span>} />
                </PieChart>
              </ResponsiveContainer>
            </GlassCard>

            {/* Identity Summary Card */}
            <GlassCard gradient>
              <div style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 16, fontWeight: 600 }}>Identity Summary</h3>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {[
                  ['Identity Version', identity?.identity_version || '--', 'indigo'],
                  ['Overall Confidence', identity?.overall_confidence ? `${Math.round(identity.overall_confidence * 100)}%` : '--', 'emerald'],
                  ['Completeness', identity?.identity_completeness ? `${Math.round(identity.identity_completeness * 100)}%` : '--', 'violet'],
                  ['Last Updated', identity?.updated_at ? new Date(identity.updated_at).toLocaleDateString() : '--', 'amber'],
                ].map(([label, value, accent]) => (
                  <div key={label} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '10px 14px', borderRadius: 8,
                    background: 'rgba(148,163,184,0.04)',
                  }}>
                    <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{label}</span>
                    <span style={{ fontSize: 15, fontWeight: 600, color: `var(--${accent}-400)` }}>{value}</span>
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>
        </>
      )}
    </div>
  )
}
