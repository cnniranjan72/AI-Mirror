import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useIdentity, useReflections, useTraces, useCognitiveMetrics, useApi } from '../hooks/useApi'
import { api } from '../api/client'
import GlassCard from '../components/ui/GlassCard'
import StatCard from '../components/ui/StatCard'
import Badge from '../components/ui/Badge'
import { ActivityIcon, BrainIcon, TargetIcon, LayersIcon, NetworkIcon, CpuIcon, RefreshIcon } from '../icons/icons'
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#10b981', '#f59e0b', '#06b6d4', '#f43f5e', '#a78bfa']

export default function Overview() {
  const navigate = useNavigate()
  const { data: profile } = useApi(() => api.getProfile())
  const { current: identity, summary: cognitiveSummary, loading: idLoading } = useIdentity()
  const { data: traces, loading: traceLoading } = useTraces()
  const { metrics } = useCognitiveMetrics()
  const { data: reflections } = useReflections()
  const { data: sessions } = useApi(() => api.getSessions())
  const { data: health } = useApi(() => api.v3Health())

  const [refreshing, setRefreshing] = useState(false)
  const handleRefresh = async () => {
    setRefreshing(true)
    setTimeout(() => setRefreshing(false), 1000)
  }

  const isLoading = idLoading && !identity && !cognitiveSummary
  const hasNoData = !idLoading && !identity && !traces?.length && !reflections?.length
  const latestTrace = traces?.[0]
  const latestReflection = reflections?.[0]
  const totalSessions = sessions?.length || 0
  const totalTraces = traces?.length || 0

  const radarData = identity?.profile ? [
    { trait: 'Openness', value: (identity.profile.openness || 0) * 100 },
    { trait: 'Conscientiousness', value: (identity.profile.conscientiousness || 0) * 100 },
    { trait: 'Extraversion', value: (identity.profile.extraversion || 0) * 100 },
    { trait: 'Agreeableness', value: (identity.profile.agreeableness || 0) * 100 },
    { trait: 'Neuroticism', value: (identity.profile.neuroticism || 0) * 100 },
  ] : [
    { trait: 'Openness', value: 0 },
    { trait: 'Conscientiousness', value: 0 },
    { trait: 'Extraversion', value: 0 },
    { trait: 'Agreeableness', value: 0 },
    { trait: 'Neuroticism', value: 0 },
  ]

  const traceLatencyData = traces?.slice(0, 10).reverse().map((t, i) => ({
    name: `#${i + 1}`, latency: t.total_ms || 0, success: t.success ? 1 : 0,
  })) || []

  const topicData = profile?.interest_distribution
    ? Object.entries(profile.interest_distribution).map(([name, value]) => ({ name, value: Math.round(value * 100) })).slice(0, 6)
    : [{ name: 'No data', value: 100 }]

  const recentActivity = sessions?.slice(0, 5).map(s => ({
    id: s.session_id || s.id,
    time: s.start_time || s.created_at,
    events: s.event_count || s.total_events || 0,
    duration: s.duration_seconds || s.total_watch_time || 0,
  })) || []

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 32 }}>
        <div>
          <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
            Cognitive Dashboard
          </h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Real-time view of your Digital Cognitive Twin</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Badge variant={health?.status === 'ok' || health?.database?.status === 'ok' ? 'emerald' : 'danger'} dot>
            {health?.status === 'ok' || health?.database?.status === 'ok' ? 'Live' : 'Offline'}
          </Badge>
          <button onClick={handleRefresh} style={{
            padding: '8px 16px', borderRadius: 8, border: '1px solid var(--border-subtle)',
            background: 'var(--bg-surface)', color: 'var(--text-secondary)', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 500,
          }}>
            <div style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }}><RefreshIcon /></div>
            Refresh
          </button>
        </div>
      </div>

      {/* Empty state banner */}
      {hasNoData && (
        <div
          className="card card-gradient"
          style={{
            padding: '40px', marginBottom: 32, textAlign: 'center',
            animation: 'fadeIn 0.5s ease-out both',
            border: '1px solid rgba(99,102,241,0.2)',
          }}
        >
          <div style={{
            width: 64, height: 64, borderRadius: 16,
            background: 'var(--accent-gradient)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 28, margin: '0 auto 16px',
            boxShadow: 'var(--shadow-glow)',
          }}>
            👋
          </div>
          <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>
            Welcome to AIMirror
          </h2>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 14, maxWidth: 480, margin: '0 auto 24px', lineHeight: 1.6 }}>
            Your cognitive dashboard is empty. Import your Instagram data or load a demo dataset to see your digital twin in action.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button
              onClick={() => navigate('/import')}
              style={{
                padding: '12px 24px', borderRadius: 10,
                background: 'var(--accent-gradient)', border: 'none',
                color: 'white', fontSize: 14, fontWeight: 600, cursor: 'pointer',
                boxShadow: 'var(--shadow-glow)',
              }}
            >
              Import Instagram Data
            </button>
            <button
              onClick={async () => {
                try {
                  await api.seedDemo()
                  window.location.reload()
                } catch (e) {
                  console.error('Seed failed:', e)
                }
              }}
              style={{
                padding: '12px 24px', borderRadius: 10,
                background: 'transparent', border: '1px solid var(--border-strong)',
                color: 'var(--text-primary)', fontSize: 14, fontWeight: 500, cursor: 'pointer',
              }}
            >
              Load Demo Data
            </button>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16, marginBottom: 32 }}>
        <StatCard label="Identity Confidence" value={identity?.overall_confidence ? `${Math.round(identity.overall_confidence * 100)}%` : '--'} icon={TargetIcon} accent="indigo" loading={isLoading} />
        <StatCard label="Identity Stability" value={cognitiveSummary?.avg_stability ? `${Math.round(cognitiveSummary.avg_stability * 100)}%` : '--'} icon={ActivityIcon} accent="violet" loading={isLoading} />
        <StatCard label="Sessions" value={totalSessions} icon={NetworkIcon} accent="pink" loading={!sessions} />
        <StatCard label="Pipeline Traces" value={totalTraces} icon={CpuIcon} accent="cyan" loading={traceLoading} />
        <StatCard label="Decisions Made" value={metrics?.filter(m => m.metric_name === 'inference_count').length || 0} icon={BrainIcon} accent="emerald" loading={false} />
        <StatCard label="Evidence Collected" value={metrics?.filter(m => m.metric_name === 'evidence_count').reduce((s, m) => s + Math.round(m.metric_value), 0) || 0} icon={LayersIcon} accent="amber" loading={false} />
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24, marginBottom: 32 }}>
        {/* Identity Radar */}
        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Identity Profile</h3>
            <Badge variant="indigo">Current Snapshot</Badge>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="rgba(148,163,184,0.15)" />
              <PolarAngleAxis dataKey="trait" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
              <Radar name="Identity" dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} strokeWidth={2} />
            </RadarChart>
          </ResponsiveContainer>
        </GlassCard>

        {/* Recent Activity */}
        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Recent Activity</h3>
            <Badge variant="neutral">{recentActivity.length} sessions</Badge>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {recentActivity.length === 0 && (
              <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>
                No recent activity
              </div>
            )}
            {recentActivity.map((act, i) => (
              <div key={act.id} style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px',
                borderRadius: 8, background: 'rgba(148,163,184,0.04)',
                animation: `fadeIn 0.3s ease-out ${i * 0.05}s both`,
              }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--indigo-400)', flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    Session {act.id?.toString().slice(0, 12)}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                    {act.events} events · {act.duration ? `${Math.round(act.duration / 60)}m` : '--'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* Second Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        {/* Pipeline Latency */}
        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Pipeline Latency</h3>
            <Badge variant="neutral">Last 10 traces</Badge>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={traceLatencyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} unit="ms" />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="latency" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>

        {/* Topic Distribution */}
        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Topic Distribution</h3>
            <Badge variant="neutral">Interests</Badge>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={topicData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                {topicData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
            {topicData.map((t, i) => (
              <Badge key={t.name} variant={['indigo', 'violet', 'pink', 'emerald', 'amber', 'cyan'][i]}>
                {t.name}
              </Badge>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* Reflection Summary */}
      <GlassCard gradient>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Latest Reflection</h3>
          <Badge variant="info" dot>AI Generated</Badge>
        </div>
        {latestReflection ? (
          <div style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.7 }}>
            <p>{latestReflection.summary || 'No summary available'}</p>
            {latestReflection.key_insights?.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>Key Insights</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {latestReflection.key_insights.slice(0, 3).map((insight, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                      <div style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--indigo-400)', marginTop: 7, flexShrink: 0 }} />
                      <span style={{ fontSize: 13 }}>{insight}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>
            No reflections yet. Ingest data to generate cognitive reflections.
          </div>
        )}
      </GlassCard>
    </div>
  )
}
