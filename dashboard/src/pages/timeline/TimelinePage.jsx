import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import LoadingSkeleton from '../../components/ui/LoadingSkeleton'
import CharacterCreature3D from '../../components/character/CharacterCreature3D'
import { SearchIcon, ClockIcon } from '../../icons/icons'

const PLATFORM_META = {
  instagram: { label: 'Instagram', icon: '📸', color: '#ec4899' },
  youtube: { label: 'YouTube', icon: '▶️', color: '#f43f5e' },
}

const ATTENTION_META = {
  deep: { label: 'Deep', variant: 'emerald' },
  shallow: { label: 'Shallow', variant: 'amber' },
  skipped: { label: 'Skipped', variant: 'neutral' },
}

const IMPACT_VARIANT = { high: 'indigo', medium: 'amber', low: 'neutral', none: 'neutral' }

function formatWhen(iso) {
  const d = new Date(iso)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  const yesterday = new Date(now); yesterday.setDate(now.getDate() - 1)
  const isYesterday = d.toDateString() === yesterday.toDateString()
  const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (sameDay) return `Today · ${time}`
  if (isYesterday) return `Yesterday · ${time}`
  return `${d.toLocaleDateString([], { month: 'short', day: 'numeric' })} · ${time}`
}

function formatWatch(seconds) {
  if (!seconds) return '0s'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return s ? `${m}m ${s}s` : `${m}m`
}

function EventCard({ ev }) {
  const [open, setOpen] = useState(false)
  const meta = PLATFORM_META[ev.platform] || { label: ev.platform, icon: '•', color: '#94a3b8' }
  const attn = ATTENTION_META[ev.attention] || ATTENTION_META.shallow
  const hasImpact = ev.behavior_objects.length > 0 || ev.evidence.length > 0 || ev.memories.length > 0
  const verb = ev.platform === 'youtube' ? (ev.surface === 'shorts' ? 'Watched (Short)' : 'Watched') : 'Watched'

  return (
    <GlassCard padding="lg" style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{formatWhen(ev.timestamp)}</span>
            <span style={{ fontSize: 13 }}>{meta.icon}</span>
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{meta.label}</span>
            <Badge variant={attn.variant}>{attn.label}</Badge>
            {ev.impact !== 'none' && <Badge variant={IMPACT_VARIANT[ev.impact]}>{ev.impact} impact</Badge>}
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
            {verb} <span style={{ fontWeight: 400, color: 'var(--text-secondary)' }}>"{ev.caption || 'untitled'}"</span>
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
            by @{ev.username || 'unknown'} · {formatWatch(ev.watch_time)} watched
            {ev.hashtags.length > 0 && <> · {ev.hashtags.slice(0, 3).join(' ')}</>}
          </div>
          <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {ev.liked && <Badge variant="pink">Liked</Badge>}
            {ev.saved && <Badge variant="indigo">Saved</Badge>}
            {ev.shared && <Badge variant="emerald">Shared</Badge>}
            {ev.commented && <Badge variant="amber">Commented</Badge>}
          </div>
        </div>
      </div>

      {hasImpact && (
        <div style={{ marginTop: 12, borderTop: '1px solid var(--border-subtle)', paddingTop: 10 }}>
          <button
            onClick={() => setOpen(o => !o)}
            style={{ background: 'none', border: 'none', color: 'var(--accent-400, #818cf8)', fontSize: 12, fontWeight: 600, cursor: 'pointer', padding: 0, display: 'flex', alignItems: 'center', gap: 6 }}
          >
            {open ? '▾' : '▸'} Identity impact
            {ev.behavior_objects.length > 0 && <Badge variant="indigo">{ev.behavior_objects.length} behavior</Badge>}
            {ev.evidence.length > 0 && <Badge variant="amber">{ev.evidence.length} evidence</Badge>}
          </button>
          {open && (
            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {ev.behavior_objects.map((bo, i) => (
                <div key={`bo-${i}`} style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ color: 'var(--text-muted)' }}>→ Behavior:</span>
                  <span style={{ color: 'var(--text-secondary)' }}>{bo.topic}</span>
                  <Badge variant="indigo">{Math.round((bo.confidence_score || 0) * 100)}% confidence</Badge>
                </div>
              ))}
              {ev.evidence.map((e, i) => (
                <div key={`ev-${i}`} style={{ fontSize: 12, display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>→ Evidence:</span>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {e.explanation} <span style={{ color: 'var(--text-muted)' }}>({Math.round((e.confidence || 0) * 100)}%)</span>
                  </span>
                </div>
              ))}
              {ev.memories.map((m, i) => (
                <div key={`mem-${i}`} style={{ fontSize: 12, display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>→ Memory:</span>
                  <span style={{ color: 'var(--text-secondary)' }}>{m.content} <span style={{ color: 'var(--text-muted)' }}>({m.memory_type})</span></span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </GlassCard>
  )
}

function FilterChip({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '6px 14px', borderRadius: 100, fontSize: 12, fontWeight: 600, cursor: 'pointer',
        border: `1px solid ${active ? 'rgba(99,102,241,0.4)' : 'var(--border-subtle)'}`,
        background: active ? 'rgba(99,102,241,0.15)' : 'transparent',
        color: active ? '#a5b4fc' : 'var(--text-tertiary)',
      }}
    >
      {children}
    </button>
  )
}

export default function TimelinePage() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState(null)
  const [nextBeforeId, setNextBeforeId] = useState(null)
  const [platform, setPlatform] = useState('')
  const [attention, setAttention] = useState('')
  const [likedOnly, setLikedOnly] = useState(false)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')

  const load = useCallback(async (opts = {}) => {
    const append = !!opts.beforeId
    if (append) setLoadingMore(true); else { setLoading(true); setEvents([]) }
    setError(null)
    try {
      const res = await api.getTimeline(undefined, {
        platform: platform || undefined,
        likedOnly: likedOnly || undefined,
        attention: attention || undefined,
        search: search || undefined,
        limit: 25,
        beforeId: opts.beforeId,
      })
      setEvents(prev => append ? [...prev, ...res.events] : res.events)
      setNextBeforeId(res.next_before_id)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load timeline')
    } finally {
      setLoading(false); setLoadingMore(false)
    }
  }, [platform, attention, likedOnly, search])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput.trim()), 400)
    return () => clearTimeout(t)
  }, [searchInput])

  const totalWithImpact = events.filter(e => e.behavior_objects.length > 0 || e.evidence.length > 0).length

  return (
    <div style={{ maxWidth: 820, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
        <div style={{ width: 68, height: 68, flexShrink: 0, margin: '-8px 0' }}>
          <CharacterCreature3D size={68} variant="pathway" confidence={events.length ? 0.7 : 0.35} thinking={loading} showLabels={false} />
        </div>
        <div>
          <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
            Digital Timeline
          </h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>
            Every watch, like, and save — and what it built in your identity
          </p>
        </div>
      </div>

      <GlassCard padding="md" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 12, position: 'relative' }}>
          <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', display: 'flex' }}>
            <SearchIcon />
          </span>
          <input
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            placeholder="Search captions or creators…"
            style={{
              flex: 1, padding: '8px 12px 8px 34px', borderRadius: 8,
              border: '1px solid var(--border-subtle)', background: 'rgba(148,163,184,0.04)',
              color: 'var(--text-primary)', fontSize: 13,
            }}
          />
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <FilterChip active={platform === ''} onClick={() => setPlatform('')}>All platforms</FilterChip>
          <FilterChip active={platform === 'instagram'} onClick={() => setPlatform('instagram')}>📸 Instagram</FilterChip>
          <FilterChip active={platform === 'youtube'} onClick={() => setPlatform('youtube')}>▶️ YouTube</FilterChip>
          <span style={{ width: 1, background: 'var(--border-subtle)', margin: '2px 4px' }} />
          <FilterChip active={attention === ''} onClick={() => setAttention('')}>Any attention</FilterChip>
          <FilterChip active={attention === 'deep'} onClick={() => setAttention('deep')}>Deep</FilterChip>
          <FilterChip active={attention === 'shallow'} onClick={() => setAttention('shallow')}>Shallow</FilterChip>
          <FilterChip active={attention === 'skipped'} onClick={() => setAttention('skipped')}>Skipped</FilterChip>
          <span style={{ width: 1, background: 'var(--border-subtle)', margin: '2px 4px' }} />
          <FilterChip active={likedOnly} onClick={() => setLikedOnly(l => !l)}>❤️ Liked only</FilterChip>
        </div>
      </GlassCard>

      {!loading && events.length > 0 && (
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
          {events.length} events · {totalWithImpact} shaped your identity
        </div>
      )}

      {loading && <LoadingSkeleton type="card" count={4} />}

      {error && (
        <GlassCard><div style={{ color: '#f87171', fontSize: 13 }}>{error}</div></GlassCard>
      )}

      {!loading && !error && events.length === 0 && (
        <GlassCard>
          <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-tertiary)' }}>
            <ClockIcon />
            <p style={{ marginTop: 12, fontSize: 14 }}>No events match these filters yet.</p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
              Browse Instagram or YouTube with the extension active, or run a demo seed from Import.
            </p>
          </div>
        </GlassCard>
      )}

      {!loading && events.map(ev => <EventCard key={ev.id} ev={ev} />)}

      {!loading && nextBeforeId && (
        <div style={{ textAlign: 'center', marginTop: 12 }}>
          <button
            onClick={() => load({ beforeId: nextBeforeId })}
            disabled={loadingMore}
            style={{
              padding: '10px 24px', borderRadius: 10, border: '1px solid var(--border-subtle)',
              background: 'transparent', color: 'var(--text-secondary)', fontSize: 13,
              cursor: loadingMore ? 'wait' : 'pointer',
            }}
          >
            {loadingMore ? 'Loading…' : 'Load older events'}
          </button>
        </div>
      )}
    </div>
  )
}
