import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import LoadingSkeleton from '../../components/ui/LoadingSkeleton'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'
import { ChevronLeftIcon, ChevronRightIcon } from '../../icons/icons'

const PLATFORM_COLOR = { instagram: '#ec4899', youtube: '#f43f5e' }

function PeriodToggle({ period, onChange }) {
  return (
    <div style={{ display: 'flex', gap: 4, padding: 3, borderRadius: 10, background: 'rgba(148,163,184,0.06)', border: '1px solid var(--border-subtle)' }}>
      {['week', 'month'].map(p => (
        <button
          key={p}
          onClick={() => onChange(p)}
          style={{
            padding: '6px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
            border: 'none', textTransform: 'capitalize',
            background: period === p ? 'var(--accent-gradient)' : 'transparent',
            color: period === p ? 'white' : 'var(--text-tertiary)',
          }}
        >
          {p}ly
        </button>
      ))}
    </div>
  )
}

function StatBar({ label, pct, color }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
        <span>{label}</span><span>{pct}%</span>
      </div>
      <div style={{ height: 6, borderRadius: 3, background: 'rgba(148,163,184,0.1)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3, transition: 'width 0.6s cubic-bezier(0.16,1,0.3,1)' }} />
      </div>
    </div>
  )
}

export default function DiaryPage() {
  const [period, setPeriod] = useState('week')
  const [offset, setOffset] = useState(0)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    api.getDiaryStory(undefined, period, offset)
      .then(setData)
      .catch(err => setError(err?.response?.data?.detail || err.message || 'Failed to load your story'))
      .finally(() => setLoading(false))
  }, [period, offset])

  useEffect(() => { load() }, [load])

  const changePeriod = (p) => { setPeriod(p); setOffset(0) }

  const stats = data?.stats
  const platforms = stats ? Object.entries(stats.platform_breakdown) : []
  const platformTotal = platforms.reduce((a, [, v]) => a + v, 0)

  return (
    <div style={{ maxWidth: 760, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
        <div style={{ width: 68, height: 68, flexShrink: 0, margin: '-8px 0' }}>
          <CharacterCreature3D size={68} variant="tome" confidence={stats?.event_count ? 0.7 : 0.35} thinking={loading} showLabels={false} />
        </div>
        <div>
          <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
            Digital Diary
          </h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>
            Your story, narrated from what actually happened
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <PeriodToggle period={period} onChange={changePeriod} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={() => setOffset(o => o + 1)}
            style={{ width: 32, height: 32, borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'transparent', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            <ChevronLeftIcon />
          </button>
          <span style={{ fontSize: 13, color: 'var(--text-tertiary)', minWidth: 140, textAlign: 'center' }}>
            {data?.label || ' '}
          </span>
          <button
            onClick={() => setOffset(o => Math.max(0, o - 1))}
            disabled={offset === 0}
            style={{ width: 32, height: 32, borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'transparent', color: offset === 0 ? 'var(--text-muted)' : 'var(--text-secondary)', cursor: offset === 0 ? 'default' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            <ChevronRightIcon />
          </button>
        </div>
      </div>

      {loading && <LoadingSkeleton type="card" count={1} />}
      {!loading && error && <GlassCard><div style={{ color: '#f87171', fontSize: 13 }}>{error}</div></GlassCard>}

      {!loading && !error && data && (
        <>
          <GlassCard gradient padding="2xl" style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--accent-400, #818cf8)', marginBottom: 14 }}>
              {data.label}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {data.story.map((line, i) => (
                <p key={i} style={{ fontSize: i === 0 ? 22 : 17, fontWeight: i === 0 ? 700 : 400, lineHeight: 1.6, color: i === 0 ? 'var(--text-primary)' : 'var(--text-secondary)', margin: 0 }}>
                  {line}
                </p>
              ))}
            </div>
          </GlassCard>

          {stats && stats.event_count > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <GlassCard>
                <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 14, color: 'var(--text-secondary)' }}>Attention</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <StatBar label="Deep" pct={stats.deep_pct} color="#34d399" />
                  <StatBar label="Shallow" pct={stats.shallow_pct} color="#fbbf24" />
                  <StatBar label="Skipped" pct={stats.skipped_pct} color="#64748b" />
                </div>
                <div style={{ marginTop: 14, fontSize: 12, color: 'var(--text-muted)' }}>
                  Avg watch time: {stats.avg_watch_time}s
                </div>
              </GlassCard>

              <GlassCard>
                <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 14, color: 'var(--text-secondary)' }}>Source Mix</h3>
                {platformTotal > 0 ? (
                  <>
                    <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', marginBottom: 10 }}>
                      {platforms.map(([p, n]) => (
                        <div key={p} style={{ width: `${(n / platformTotal) * 100}%`, background: PLATFORM_COLOR[p] || '#94a3b8' }} />
                      ))}
                    </div>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      {platforms.map(([p, n]) => (
                        <Badge key={p} variant="neutral">{p === 'youtube' ? '▶️' : '📸'} {p} {n}</Badge>
                      ))}
                    </div>
                  </>
                ) : <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>No platform data</div>}
              </GlassCard>

              {stats.top_topics.length > 0 && (
                <GlassCard>
                  <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 14, color: 'var(--text-secondary)' }}>Top Topics</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {stats.top_topics.map((t, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                        <span style={{ color: 'var(--text-secondary)' }}>{t.topic}</span>
                        <span style={{ color: 'var(--text-muted)' }}>{t.events} events</span>
                      </div>
                    ))}
                  </div>
                </GlassCard>
              )}

              {stats.top_creators.length > 0 && (
                <GlassCard>
                  <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 14, color: 'var(--text-secondary)' }}>Top Creators</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {stats.top_creators.map((c, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                        <span style={{ color: 'var(--text-secondary)' }}>@{c.username}</span>
                        <span style={{ color: 'var(--text-muted)' }}>{c.events} events</span>
                      </div>
                    ))}
                  </div>
                </GlassCard>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
