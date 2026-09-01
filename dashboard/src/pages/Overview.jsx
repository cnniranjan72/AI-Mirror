import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useIdentity, useReflections, useTraces, useApi } from '../hooks/useApi'
import { api } from '../api/client'
import GlassCard from '../components/ui/GlassCard'
import StatCard from '../components/ui/StatCard'
import Badge from '../components/ui/Badge'
import { ActivityIcon, BrainIcon, TargetIcon, LayersIcon, NetworkIcon, CpuIcon, RefreshIcon } from '../icons/icons'
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import CharacterCreature3D from '../components/character/CharacterCreature3D'
import Reveal from '../components/motion/Reveal'

// Shared tooltip chrome — the charts on this page were each carrying their own
// copy of these three style objects.
const TOOLTIP_STYLE = {
  contentStyle: { background: 'rgba(15,23,42,0.94)', border: '1px solid rgba(148,163,184,0.22)', borderRadius: 10, fontSize: 12, backdropFilter: 'blur(10px)', boxShadow: '0 12px 32px -8px rgba(2,6,23,0.8)' },
  labelStyle: { color: '#e2e8f0' },
  itemStyle: { color: '#e2e8f0' },
}

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#10b981', '#f59e0b', '#06b6d4', '#f43f5e', '#a78bfa']

const parseJSON = (v) => {
  if (v == null) return {}
  if (typeof v === 'object') return v
  try { return JSON.parse(v) } catch { return {} }
}

export default function Overview() {
  const navigate = useNavigate()
  const { current: identityRaw, summary, loading: idLoading, error: idError, refetch: refetchIdentity } = useIdentity()
  const { data: traces, loading: traceLoading } = useTraces()
  const { data: reflections } = useReflections()
  const { data: health, loading: healthLoading } = useApi(() => api.v3Health())

  const [refreshing, setRefreshing] = useState(false)
  const handleRefresh = () => { setRefreshing(true); setTimeout(() => setRefreshing(false), 800) }

  // /identity/current wraps the identity object; unwrap it.
  const identity = identityRaw?.identity || identityRaw || null
  const behaviorProfile = parseJSON(identity?.behavior_profile)
  const interestGraph = parseJSON(identity?.interest_graph)

  // health starts null until the request resolves — reading that as "Offline"
  // misrepresents "still checking" as "confirmed down" on every page load.
  const online = health?.status === 'ok' || health?.status === 'healthy' || health?.database?.status === 'healthy'
  const isLoading = idLoading && !identity && !summary
  // A fetch failure isn't "no data" — showing the welcome banner on an error
  // would misleadingly read as "you have a fresh, empty account" instead of
  // "something's broken."
  const hasNoData = !idLoading && !idError && !summary?.behavior_object_count && !identity && !(traces?.length)

  const confidence = summary?.current_identity?.overall_confidence ?? identity?.overall_confidence
  const identityVersion = summary?.current_identity?.identity_version ?? identity?.identity_version
  // dominant_topics / dominant_interests may arrive as JSON strings.
  const dtParsed = parseJSON(identity?.dominant_topics)
  const dominantTopics = Array.isArray(dtParsed) ? dtParsed : (Array.isArray(identity?.dominant_topics) ? identity.dominant_topics : [])
  const domInterests = Array.isArray(interestGraph.dominant_interests) ? interestGraph.dominant_interests : []
  const latestReflection = reflections?.[0]

  // Cognitive profile radar — built from real, available identity metrics.
  const radarData = [
    { trait: 'Confidence', value: Math.round((identity?.overall_confidence || 0) * 100) },
    { trait: 'Completeness', value: Math.round((identity?.identity_completeness || 0) * 100) },
    { trait: 'Engagement', value: Math.round((behaviorProfile.avg_engagement_rate || 0) * 100) },
    { trait: 'Diversity', value: Math.round((behaviorProfile.behavior_diversity ?? interestGraph.diversity_score ?? 0) * 100) },
    { trait: 'Stability', value: Math.round((behaviorProfile.behavior_stability || 0) * 100) },
  ]

  // dominant_interests items carry `strength` (0-1), not `weight`/`score` — this
  // was the mismatch that made the pie always fall back to an equal split.
  const topicData = dominantTopics.length
    ? dominantTopics.slice(0, 6).map((name) => {
        const di = domInterests.find(d => d.topic === name)
        const s = di?.strength
        return { name, value: typeof s === 'number' ? Math.max(3, Math.round(s * 100)) : Math.round(100 / Math.min(dominantTopics.length, 6)) }
      })
    : [{ name: 'No data', value: 100 }]

  const traceLatencyData = (traces || []).slice(0, 10).reverse().map((t, i) => ({
    name: `#${i + 1}`, latency: Math.round(t.total_ms || t.total_time_ms || 0),
  }))

  const recentActivity = (traces || []).slice(0, 6).map(t => ({
    id: t.trace_id || t.id,
    query: t.query || '(query)',
    intent: t.intent_type || '',
    time: t.created_at || t.started_at,
    success: t.success !== false,
  }))

  return (
    <div>
      {/* Header */}
      <Reveal variant="depth">
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: 32, flexWrap: 'wrap', gap: 16,
          position: 'relative',
        }}>
          {/* Ambient pool behind the creature, tying the page header into the
              WebGL field rendering behind the whole app. */}
          <div className="halo" style={{ width: 260, height: 260, top: -90, left: -60, background: 'rgba(99,102,241,0.20)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 14, position: 'relative' }}>
            <div style={{ width: 76, height: 76, flexShrink: 0, margin: '-8px 0' }}>
              <CharacterCreature3D size={76} variant="pulse" confidence={confidence ?? 0.4} thinking={isLoading} showLabels={false} />
            </div>
            <div>
              <h1 className="display-title" style={{ fontSize: 36, fontWeight: 800, marginBottom: 6, lineHeight: 1.1 }}>
                Cognitive Dashboard
              </h1>
              <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Real-time view of your Digital Cognitive Twin</p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Badge variant={healthLoading ? 'neutral' : online ? 'emerald' : 'danger'} dot>
              {healthLoading ? 'Checking...' : online ? 'Live' : 'Offline'}
            </Badge>
            <button onClick={handleRefresh} className="btn-3d" style={{
              padding: '9px 18px', borderRadius: 10, border: '1px solid var(--border-subtle)',
              background: 'var(--bg-surface)', color: 'var(--text-secondary)', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 500,
              backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
            }}>
              <div style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }}><RefreshIcon /></div>
              Refresh
            </button>
          </div>
        </div>
      </Reveal>

      {/* Error banner — distinct from the empty-state welcome below */}
      {idError && (
        <div className="empty-state" style={{ marginBottom: 32 }}>
          <div className="empty-state-icon">⚠️</div>
          <div className="empty-state-title">Couldn't load your dashboard</div>
          <div className="empty-state-description">{typeof idError === 'string' ? idError : 'Something went wrong talking to the backend.'}</div>
          <button className="btn btn-secondary" onClick={refetchIdentity} style={{ marginTop: 16 }}>Try again</button>
        </div>
      )}

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
          </div>
        </div>
      )}

      {/* Stats Grid — all sourced from /cognitive/summary */}
      <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16, marginBottom: 32 }}>
        <StatCard label="Identity Confidence" value={confidence != null ? `${Math.round(confidence * 100)}%` : '--'} icon={TargetIcon} accent="indigo" loading={isLoading} />
        <StatCard label="Identity Version" value={identityVersion != null ? `v${identityVersion}` : '--'} icon={ActivityIcon} accent="violet" loading={isLoading} />
        <StatCard label="Behavior Objects" value={summary?.behavior_object_count ?? 0} icon={NetworkIcon} accent="pink" loading={!summary} />
        <StatCard label="Evidence Collected" value={summary?.evidence_count ?? 0} icon={LayersIcon} accent="amber" loading={!summary} />
        <StatCard label="Snapshots" value={summary?.snapshot_count ?? 0} icon={CpuIcon} accent="cyan" loading={!summary} />
        <StatCard label="Pipeline Traces" value={summary?.trace_count ?? (traces?.length || 0)} icon={BrainIcon} accent="emerald" loading={traceLoading} />
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24, marginBottom: 32 }}>
        {/* Cognitive Profile Radar */}
        <Reveal variant="depth" style={{ height: '100%' }}>
        <GlassCard gradient style={{ height: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Cognitive Profile</h3>
            <Badge variant="indigo">v{identityVersion ?? '?'}</Badge>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarData}>
              <defs>
                <radialGradient id="radarFill" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.45} />
                  <stop offset="60%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.12} />
                </radialGradient>
              </defs>
              <PolarGrid stroke="rgba(148,163,184,0.15)" />
              <PolarAngleAxis dataKey="trait" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
              <Radar
                name="Identity" dataKey="value"
                stroke="#818cf8" fill="url(#radarFill)" fillOpacity={1} strokeWidth={2}
                dot={{ r: 3, fill: '#22d3ee', stroke: 'none' }}
                isAnimationActive animationDuration={900} animationEasing="ease-out"
              />
              <Tooltip {...TOOLTIP_STYLE} />
            </RadarChart>
          </ResponsiveContainer>
        </GlassCard>
        </Reveal>

        {/* Recent Activity — recent pipeline queries */}
        <Reveal variant="depth" delay={110} style={{ height: '100%' }}>
        <GlassCard gradient style={{ height: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Recent Queries</h3>
            <Badge variant="neutral">{recentActivity.length}</Badge>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {recentActivity.length === 0 && (
              <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>
                No queries yet — try the Chat page
              </div>
            )}
            {recentActivity.map((act, i) => (
              <div
                key={act.id || i}
                onClick={() => act.id && navigate(`/trace/${act.id}`)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px',
                  borderRadius: 10, background: 'rgba(148,163,184,0.04)', cursor: act.id ? 'pointer' : 'default',
                  border: '1px solid transparent',
                  animation: `fadeIn 0.3s ease-out ${i * 0.05}s both`,
                  transition: 'background var(--dur-fast) var(--ease-swift), border-color var(--dur-fast) var(--ease-swift), transform var(--dur-fast) var(--ease-spring)',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'rgba(99,102,241,0.10)'
                  e.currentTarget.style.borderColor = 'rgba(99,102,241,0.28)'
                  e.currentTarget.style.transform = 'translateX(3px)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(148,163,184,0.04)'
                  e.currentTarget.style.borderColor = 'transparent'
                  e.currentTarget.style.transform = 'none'
                }}
              >
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: act.success ? 'var(--emerald-400, #10b981)' : 'var(--danger, #f43f5e)', flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {act.query}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                    {act.intent || 'query'}{act.time ? ` · ${new Date(act.time).toLocaleTimeString()}` : ''}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
        </Reveal>
      </div>

      {/* Second Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        {/* Pipeline Latency */}
        <Reveal variant="depth" style={{ height: '100%' }}>
        <GlassCard gradient style={{ height: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Pipeline Latency</h3>
            <Badge variant="neutral">Last 10 traces</Badge>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={traceLatencyData}>
              <defs>
                <linearGradient id="barLatency" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.95} />
                  <stop offset="55%" stopColor="#6366f1" stopOpacity={0.85} />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.35} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} unit="ms" />
              <Tooltip {...TOOLTIP_STYLE} cursor={{ fill: 'rgba(99,102,241,0.08)' }} />
              <Bar
                dataKey="latency" fill="url(#barLatency)" radius={[5, 5, 0, 0]}
                isAnimationActive animationDuration={800} animationEasing="ease-out"
              />
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>
        </Reveal>

        {/* Topic Distribution */}
        <Reveal variant="depth" delay={110} style={{ height: '100%' }}>
        <GlassCard gradient style={{ height: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Topic Distribution</h3>
            <Badge variant="neutral">Interests</Badge>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={topicData} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                paddingAngle={3} dataKey="value" stroke="rgba(2,6,23,0.5)" strokeWidth={1}
                isAnimationActive animationDuration={850} animationEasing="ease-out"
              >
                {topicData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip {...TOOLTIP_STYLE} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
            {topicData.map((t, i) => (
              <Badge key={t.name} variant={['indigo', 'violet', 'pink', 'emerald', 'amber', 'cyan'][i % 6]}>
                {t.name}
              </Badge>
            ))}
          </div>
        </GlassCard>
        </Reveal>
      </div>

      {/* Reflection Summary */}
      <Reveal variant="depth">
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
      </Reveal>
    </div>
  )
}
