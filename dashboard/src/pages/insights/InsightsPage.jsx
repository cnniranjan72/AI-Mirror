import { useState } from 'react'
import { useApi } from '../../hooks/useApi'
import { api, activeUser } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import { DownloadIcon, TargetIcon, NetworkIcon, LayersIcon } from '../../icons/icons'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'

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
  const { data: profile, loading, error, refetch } = useApi(() => api.getInsightsProfile(), [])
  const [expanded, setExpanded] = useState(null)

  const [campaignText, setCampaignText] = useState('')
  const [resonance, setResonance] = useState(null)
  const [resonanceLoading, setResonanceLoading] = useState(false)
  const [resonanceError, setResonanceError] = useState(null)

  const runResonance = async () => {
    if (!campaignText.trim()) return
    setResonanceLoading(true)
    setResonanceError(null)
    try {
      const res = await api.postCampaignResonance(campaignText)
      setResonance(res)
    } catch (err) {
      setResonanceError(err?.response?.data?.detail || err.message)
    } finally {
      setResonanceLoading(false)
    }
  }

  const resonanceColor = (pct) => (pct >= 60 ? '#10b981' : pct >= 30 ? '#f59e0b' : '#f43f5e')

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
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 32 }}>
        <div style={{ width: 72, height: 72, flexShrink: 0, margin: '-10px 0' }}>
          <CharacterCreature3D
            size={72}
            variant="crystal"
            confidence={profile?.identity?.overall_confidence ?? 0.3}
            topics={profile?.audience_segment?.tags ?? []}
            thinking={loading}
            showLabels={false}
          />
        </div>
        <div>
          <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>Insights Export</h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>
            The algorithmic identity profile — structured, source-cited, and exportable
          </p>
        </div>
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
        ) : error ? (
          <div style={{ padding: 24, textAlign: 'center' }}>
            <div style={{ color: '#f87171', fontSize: 13, marginBottom: 10 }}>Couldn't build the profile: {typeof error === 'string' ? error : 'request failed'}</div>
            <button className="btn btn-secondary" onClick={refetch}>Try again</button>
          </div>
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

      {/* Campaign resonance simulator */}
      <GlassCard gradient style={{ marginTop: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Campaign Resonance Simulator</h3>
          <Badge variant="neutral">deterministic, no LLM</Badge>
        </div>
        <p style={{ fontSize: 12.5, color: 'var(--text-tertiary)', marginBottom: 16, lineHeight: 1.6 }}>
          Describe a hypothetical product, content piece, or outreach message. It's scored against
          this user's real dominant topics, creator affinity, and motivation signals — a pre-spend
          fit check, not a guess.
        </p>
        <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <textarea
            value={campaignText}
            onChange={e => setCampaignText(e.target.value)}
            placeholder="e.g. New Rust systems-programming course — build advanced projects, learn from ai_explained-style teaching"
            rows={2}
            style={{
              flex: 1, padding: '10px 14px', borderRadius: 10,
              background: '#1e293b', border: '1px solid var(--border-strong, rgba(148,163,184,0.25))',
              color: '#f8fafc', caretColor: '#818cf8', colorScheme: 'dark',
              fontSize: 13, outline: 'none', resize: 'none', fontFamily: 'var(--font-sans)', lineHeight: 1.5,
            }}
          />
          <button onClick={runResonance} disabled={!campaignText.trim() || resonanceLoading} style={{
            padding: '10px 18px', borderRadius: 10, border: 'none',
            background: campaignText.trim() && !resonanceLoading ? 'var(--accent-gradient)' : 'rgba(148,163,184,0.1)',
            color: 'white', fontSize: 13, fontWeight: 600,
            cursor: campaignText.trim() && !resonanceLoading ? 'pointer' : 'not-allowed',
            opacity: campaignText.trim() && !resonanceLoading ? 1 : 0.5, flexShrink: 0,
          }}>
            {resonanceLoading ? 'Scoring…' : 'Simulate'}
          </button>
        </div>

        {resonanceError && (
          <div style={{ padding: '10px 14px', borderRadius: 8, background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#f87171', fontSize: 13, marginBottom: 12 }}>
            {resonanceError}
          </div>
        )}

        {resonance && !resonanceError && (
          <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>
            <div style={{
              width: 84, height: 84, borderRadius: '50%', display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              background: `${resonanceColor(resonance.resonance_pct)}18`, border: `2px solid ${resonanceColor(resonance.resonance_pct)}`,
            }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: resonanceColor(resonance.resonance_pct) }}>{resonance.resonance_pct}%</div>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase' }}>resonance</div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', gap: 16, marginBottom: 12, flexWrap: 'wrap' }}>
                {Object.entries(resonance.breakdown).map(([k, v]) => (
                  <div key={k} style={{ minWidth: 130 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'capitalize' }}>{k.replace('_', ' ')}</div>
                    <div style={{ height: 6, background: 'rgba(148,163,184,0.1)', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{ width: `${Math.round(v * 100)}%`, height: '100%', background: resonanceColor(Math.round(v * 100)) }} />
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {resonance.explanation.map((e, i) => (
                  <div key={i} style={{ fontSize: 12.5, color: 'var(--text-secondary)', display: 'flex', gap: 6 }}>
                    <span style={{ color: 'var(--text-muted)' }}>•</span> {e}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </GlassCard>

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
