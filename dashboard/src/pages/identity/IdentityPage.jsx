import { useState } from 'react'
import { useIdentity, useCognitiveMetrics } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import StatCard from '../../components/ui/StatCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'
import { TargetIcon, ActivityIcon, BrainIcon, ClockIcon, LayersIcon } from '../../icons/icons'
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, Area } from 'recharts'
import IdentityInspector from '../../components/explain/IdentityInspector'
import IdentityEvolution from '../../components/identity/IdentityEvolution'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'
import IdentityGalaxy from '../../components/identity/IdentityGalaxy'

const parseJSON = (v) => {
  if (v == null) return {}
  if (typeof v === 'object') return v
  try { return JSON.parse(v) } catch { return {} }
}

const subProfiles = [
  { key: 'behavior_profile', label: 'Behavior Profile', fields: ['avg_engagement_rate', 'behavior_diversity', 'behavior_stability'] },
  { key: 'interest_graph', label: 'Interest Graph', fields: ['diversity_score', 'total_topics'] },
  { key: 'creator_graph', label: 'Creator Graph', fields: ['creator_diversity_score', 'dependence_score'] },
  { key: 'learning_style', label: 'Learning Style', fields: ['confidence', 'completion_rate'] },
  { key: 'attention_profile', label: 'Attention Profile', fields: ['avg_attention_span', 'focus_quality'] },
]

export default function IdentityPage() {
  const { current: identityData, snapshots, summary: cognitiveSummary, loading, error, refetch } = useIdentity()
  const [inspectingIdentity, setInspectingIdentity] = useState(null)
  const [view, setView] = useState('overview')
  const [selectedTopic, setSelectedTopic] = useState(null)

  // /identity/current wraps the identity object.
  const identity = identityData?.identity || identityData
  const identityId = identity?.identity_id || identityData?.latest_snapshot?.identity_id
  const snapshotList = snapshots || []

  const behaviorProfile = parseJSON(identity?.behavior_profile)
  const interestGraph = parseJSON(identity?.interest_graph)
  const attentionProfile = parseJSON(identity?.attention_profile)
  const avgStability = behaviorProfile.behavior_stability

  // Big Five is not modeled; show real cognitive dimensions instead.
  const radarData = [
    { trait: 'Confidence', value: Math.round((identity?.overall_confidence || 0) * 100) },
    { trait: 'Completeness', value: Math.round((identity?.identity_completeness || 0) * 100) },
    { trait: 'Engagement', value: Math.round((behaviorProfile.avg_engagement_rate || 0) * 100) },
    { trait: 'Diversity', value: Math.round((behaviorProfile.behavior_diversity ?? interestGraph.diversity_score ?? 0) * 100) },
    { trait: 'Focus', value: Math.round((attentionProfile.focus_quality || 0) * 100) },
    { trait: 'Stability', value: Math.round((behaviorProfile.behavior_stability || 0) * 100) },
  ]

  const dominantInterests = interestGraph.dominant_interests || []
  const selectedInterest = dominantInterests.find(t => t.topic === selectedTopic)

  const versionHistory = snapshotList.map((s) => ({
    version: s.identity_version,
    confidence: s.confidence ?? s.overall_confidence ?? 0,
    completeness: s.identity_completeness ?? 0,
    timestamp: s.snapshot_timestamp || s.created_at,
  })).reverse()

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 68, height: 68, flexShrink: 0, margin: '-8px 0' }}>
              <CharacterCreature3D size={68} variant="helix" confidence={identity?.overall_confidence ?? 0.4} thinking={loading} showLabels={false} />
            </div>
            <div>
              <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Identity</h1>
              <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>Cognitive identity profile and evolution tracking</p>
            </div>
          </div>
          {snapshotList.length >= 2 && (
            <div style={{ display: 'flex', gap: 4, background: 'var(--bg-surface)', borderRadius: 8, padding: 2, border: '1px solid var(--border-subtle)' }}>
              {['overview', 'evolution'].map(v => (
                <button key={v} onClick={() => setView(v)} style={{
                  padding: '6px 14px', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 500,
                  background: view === v ? 'var(--indigo-500)' : 'transparent',
                  color: view === v ? 'white' : 'var(--text-muted)',
                  transition: 'all 0.15s',
                }}>{v === 'overview' ? 'Overview' : 'Evolution'}</button>
              ))}
            </div>
          )}
        </div>
      </div>

      <AsyncState loading={loading} error={error} onRetry={refetch}>
      {view === 'overview' && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16, marginBottom: 32 }}>
            <StatCard label="Identity Confidence" value={identity?.overall_confidence ? `${Math.round(identity.overall_confidence * 100)}%` : '--'} icon={TargetIcon} accent="indigo" loading={loading}
              onClick={identityId ? () => setInspectingIdentity(identityId) : undefined} />
            <StatCard label="Completeness" value={identity?.identity_completeness ? `${Math.round(identity.identity_completeness * 100)}%` : '--'} icon={ActivityIcon} accent="violet" loading={loading}
              onClick={identityId ? () => setInspectingIdentity(identityId) : undefined} />
            <StatCard label="Avg Stability" value={typeof avgStability === 'number' ? `${Math.round(avgStability * 100)}%` : '--'} icon={BrainIcon} accent="emerald" loading={loading} />
            <StatCard label="Version" value={identity?.identity_version ? `v${identity.identity_version}` : (cognitiveSummary?.current_identity?.identity_version ? `v${cognitiveSummary.current_identity.identity_version}` : '--')} icon={LayersIcon} accent="cyan" loading={loading} />
            <StatCard label="Snapshots" value={snapshotList.length} icon={ClockIcon} accent="amber" loading={loading} />
          </div>

      <GlassCard gradient style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Identity Galaxy</h3>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              Each planet is a real dominant interest — size is strength, color is trend, distance is rank. Drag to rotate, click a planet.
            </p>
          </div>
          <Badge variant="indigo">{dominantInterests.length} interests</Badge>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: selectedInterest ? '1fr 240px' : '1fr', gap: 16 }}>
          <IdentityGalaxy
            topics={dominantInterests}
            confidence={identity?.overall_confidence || 0}
            selectedTopic={selectedTopic}
            onSelectTopic={(t) => setSelectedTopic(t.topic === selectedTopic ? null : t.topic)}
            style={{ height: 380, borderRadius: 12, overflow: 'hidden', background: 'radial-gradient(circle at 50% 40%, rgba(30,27,75,0.4), rgba(2,6,23,0.5))' }}
          />
          {selectedInterest && (
            <div style={{ padding: 14, borderRadius: 12, background: 'rgba(148,163,184,0.05)', border: '1px solid var(--border-subtle)' }}>
              <h4 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>{selectedInterest.topic}</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-muted)' }}>Trend</span><span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{selectedInterest.trend}</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-muted)' }}>Strength</span><span style={{ color: 'var(--text-secondary)' }}>{Math.round((selectedInterest.strength || 0) * 100)}%</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-muted)' }}>Confidence</span><span style={{ color: 'var(--text-secondary)' }}>{Math.round((selectedInterest.confidence || 0) * 100)}%</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-muted)' }}>Frequency</span><span style={{ color: 'var(--text-secondary)' }}>{selectedInterest.frequency}</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-muted)' }}>Engagement</span><span style={{ color: 'var(--text-secondary)' }}>{Math.round((selectedInterest.engagement_rate || 0) * 100)}%</span></div>
              </div>
            </div>
          )}
        </div>
      </GlassCard>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Cognitive Profile</h3>
            <Badge variant="indigo">Identity dimensions</Badge>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="rgba(148,163,184,0.12)" />
              <PolarAngleAxis dataKey="trait" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
              <Radar name="Profile" dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} strokeWidth={2} />
              <Radar name="Baseline" dataKey="value" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.1} strokeWidth={1} strokeDasharray="4 4" />
            </RadarChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard gradient>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600 }}>Identity Evolution</h3>
            <Badge variant="neutral">Confidence + completeness over versions</Badge>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={versionHistory}>
              <defs>
                <linearGradient id="colorConf" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorComplete" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey="version" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} label={{ value: 'Version', position: 'bottom', fill: '#64748b', fontSize: 11 }} />
              <YAxis domain={[0, 1]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, fontSize: 12 }} labelStyle={{ color: '#e2e8f0' }} itemStyle={{ color: '#e2e8f0' }} />
              <Area type="monotone" dataKey="confidence" name="Confidence" stroke="#6366f1" fill="url(#colorConf)" strokeWidth={2} />
              <Area type="monotone" dataKey="completeness" name="Completeness" stroke="#10b981" fill="url(#colorComplete)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>
      </div>

      <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>Sub-Profile Details</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16, marginBottom: 32 }}>
        {subProfiles.map(sp => {
          const sub = parseJSON(identity?.[sp.key])
          if (!sub || Object.keys(sub).length === 0) return null
          return (
            <GlassCard key={sp.key}>
              <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>{sp.label}</h4>
              {sp.fields.map(f => (
                <div key={f} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: 13 }}>
                  <span style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>{f.replace(/_/g, ' ')}</span>
                  <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{sub[f] !== undefined ? Math.round(sub[f] * 100) / 100 : '--'}</span>
                </div>
              ))}
            </GlassCard>
          )
        })}
      </div>

      <GlassCard gradient>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Snapshot Explorer</h3>
          <Badge variant="neutral">{snapshotList.length} snapshots</Badge>
        </div>
        {snapshotList.length === 0 ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>No identity snapshots yet</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {snapshotList.slice(-10).reverse().map((s, i) => (
              <div key={s.snapshot_id || i} style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px',
                borderRadius: 8, background: 'rgba(148,163,184,0.04)',
                animation: `fadeIn 0.3s ease-out ${i * 0.04}s both`,
              }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--indigo-400)', flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500 }}>
                    v{s.snapshot_version || s.version || i + 1}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {s.snapshot_timestamp || s.created_at ? new Date(s.snapshot_timestamp || s.created_at).toLocaleString() : '--'}
                  </div>
                </div>
                <Badge variant={s.confidence > 0.7 ? 'emerald' : s.confidence > 0.4 ? 'warning' : 'danger'}>
                  {s.confidence ? `${Math.round(s.confidence * 100)}%` : '--'}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </GlassCard>

        </>
      )}

      {view === 'evolution' && (
        <GlassCard gradient padding="2xl">
          <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 20 }}>Identity Evolution Timeline</h3>
          <IdentityEvolution snapshots={snapshotList} />
        </GlassCard>
      )}
      </AsyncState>

      {inspectingIdentity && (
        <IdentityInspector identityId={inspectingIdentity} onClose={() => setInspectingIdentity(null)} />
      )}
    </div>
  )
}
