import { useState } from 'react'
import { useApi } from '../../hooks/useApi'
import { api, activeUser } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import { DownloadIcon, TargetIcon, NetworkIcon, LayersIcon } from '../../icons/icons'

const USE_CASES = [
  {
    title: 'Ad & Marketing Agencies',
    icon: '🎯',
    desc: 'Audience segment tags, interest & creator-affinity graph, and behavioral alignment for precision outreach — without raw personal data.',
    fields: ['audience_segment', 'interests', 'creator_affinity'],
  },
  {
    title: 'Mental Health & Wellbeing Research',
    icon: '🧠',
    desc: 'Explainable risk indicators (engagement depth, late-night usage, sensitive-content exposure) for studying platform impact at scale.',
    fields: ['wellbeing_signal', 'cognitive_signals'],
  },
  {
    title: 'Academic & Behavioral Research',
    icon: '🔬',
    desc: 'The full algorithmic-identity schema — every field cites its source table — plus raw CSV export for reproducible analysis.',
    fields: ['identity', 'cognitive_signals', 'interests'],
  },
]

const TABLES = ['behavior_objects', 'evidence', 'inferences', 'reflections']

export default function InsightsPage() {
  const { data: profile, loading } = useApi(() => api.getInsightsProfile(), [])
  const [expanded, setExpanded] = useState(null)

  const downloadJson = () => {
    const blob = new Blob([JSON.stringify(profile, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${activeUser()}_algorithmic_identity.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Insights Export</h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>
          The algorithmic identity profile — structured, source-cited, and exportable
        </p>
      </div>

      {/* Use case cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16, marginBottom: 32 }}>
        {USE_CASES.map(uc => (
          <GlassCard key={uc.title}>
            <div style={{ fontSize: 28, marginBottom: 10 }}>{uc.icon}</div>
            <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>{uc.title}</h4>
            <p style={{ fontSize: 12.5, color: 'var(--text-tertiary)', lineHeight: 1.6 }}>{uc.desc}</p>
          </GlassCard>
        ))}
      </div>

      {/* Export actions */}
      <GlassCard gradient>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Export</h3>
          <Badge variant="neutral">schema v{profile?.schema_version || '1.0'}</Badge>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 20 }}>
          <button onClick={downloadJson} disabled={!profile} style={{
            padding: '10px 18px', borderRadius: 10, border: 'none',
            background: 'var(--accent-gradient)', color: 'white', fontSize: 13, fontWeight: 600,
            cursor: profile ? 'pointer' : 'not-allowed', display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <DownloadIcon /> Full Profile (JSON)
          </button>
          {TABLES.map(t => (
            <a key={t} href={api.exportCsvUrl(activeUser(), t)} download
              style={{
                padding: '10px 16px', borderRadius: 10, border: '1px solid var(--border-subtle)',
                background: 'transparent', color: 'var(--text-secondary)', fontSize: 13,
                textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 8,
              }}>
              <DownloadIcon /> {t.replace('_', ' ')}.csv
            </a>
          ))}
        </div>

        {loading ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>Building profile…</div>
        ) : profile && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
            <MiniStat label="Identity confidence" value={`${Math.round((profile.identity.overall_confidence || 0) * 100)}%`} icon={TargetIcon} />
            <MiniStat label="Persona" value={profile.identity.persona_label || '—'} icon={LayersIcon} />
            <MiniStat label="Top creators tracked" value={profile.creator_affinity.top_creators.length} icon={NetworkIcon} />
            <MiniStat label="Wellbeing risk" value={profile.wellbeing_signal.risk_level} icon={TargetIcon} />
          </div>
        )}
      </GlassCard>

      {/* Segment tags */}
      {profile && (
        <GlassCard gradient style={{ marginTop: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Audience Segment</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
            {profile.audience_segment.tags.map(t => <Badge key={t} variant="indigo">{t}</Badge>)}
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>{profile.audience_segment.note}</p>
        </GlassCard>
      )}

      {/* Raw schema browser */}
      {profile && (
        <GlassCard gradient style={{ marginTop: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Schema Browser</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {Object.entries(profile).filter(([k]) => typeof profile[k] === 'object' && profile[k] !== null && !Array.isArray(profile[k])).map(([key, val]) => (
              <div key={key}>
                <button
                  onClick={() => setExpanded(expanded === key ? null : key)}
                  style={{
                    width: '100%', textAlign: 'left', padding: '10px 14px', borderRadius: 8,
                    background: 'rgba(148,163,184,0.04)', border: '1px solid var(--border-subtle)',
                    color: 'var(--text-secondary)', fontSize: 13, cursor: 'pointer',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}
                >
                  <span style={{ fontWeight: 600 }}>{key}</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{val.source || ''}</span>
                </button>
                {expanded === key && (
                  <pre style={{
                    marginTop: 6, padding: 12, borderRadius: 8, background: 'rgba(0,0,0,0.25)',
                    fontSize: 11, color: 'var(--text-tertiary)', overflow: 'auto', maxHeight: 260,
                  }}>{JSON.stringify(val, null, 2)}</pre>
                )}
              </div>
            ))}
          </div>
        </GlassCard>
      )}
    </div>
  )
}

function MiniStat({ label, value, icon: Icon }) {
  return (
    <div style={{ padding: 14, borderRadius: 10, background: 'rgba(148,163,184,0.04)', border: '1px solid var(--border-subtle)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)', fontSize: 11, marginBottom: 6, textTransform: 'uppercase' }}>
        <Icon /> {label}
      </div>
      <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{value}</div>
    </div>
  )
}
