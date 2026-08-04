import { useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import Badge from '../ui/Badge'

const PLATFORM_ICON = { instagram: '📸', youtube: '▶️' }

function timeAgo(iso) {
  if (!iso) return ''
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000))
  if (seconds < 5) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  const mins = Math.floor(seconds / 60)
  if (mins < 60) return `${mins}m ago`
  return `${Math.floor(mins / 60)}h ago`
}

/**
 * Polls GET /timeline?limit=1 every few seconds and flashes only when the
 * newest event's real id actually changes — no fake/simulated ticks. There's
 * no websocket layer in this backend, so polling-with-real-diff is the
 * honest version of "real-time" available here.
 */
export default function LiveIngestionPulse() {
  const [latest, setLatest] = useState(null)
  const [flash, setFlash] = useState(false)
  const [seenCount, setSeenCount] = useState(0)
  const [, forceTick] = useState(0)
  const lastIdRef = useRef(null)
  const flashTimeoutRef = useRef(null)

  useEffect(() => {
    let cancelled = false

    const poll = async () => {
      try {
        const res = await api.getTimeline(undefined, { limit: 1 })
        if (cancelled) return
        const ev = res.events?.[0]
        if (!ev) return
        if (lastIdRef.current !== null && ev.id !== lastIdRef.current) {
          setSeenCount(c => c + 1)
          setFlash(true)
          clearTimeout(flashTimeoutRef.current)
          flashTimeoutRef.current = setTimeout(() => setFlash(false), 1400)
        }
        lastIdRef.current = ev.id
        setLatest(ev)
      } catch { /* silent — this is a passive background indicator */ }
    }

    poll()
    const pollId = setInterval(poll, 6000)
    const tickId = setInterval(() => forceTick(t => t + 1), 5000) // refresh "Xs ago" text
    return () => { cancelled = true; clearInterval(pollId); clearInterval(tickId); clearTimeout(flashTimeoutRef.current) }
  }, [])

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderRadius: 10,
      background: flash ? 'rgba(52,211,153,0.1)' : 'rgba(148,163,184,0.04)',
      border: `1px solid ${flash ? 'rgba(52,211,153,0.3)' : 'var(--border-subtle)'}`,
      transition: 'background 0.4s ease, border-color 0.4s ease',
    }}>
      <div style={{ position: 'relative', width: 10, height: 10, flexShrink: 0 }}>
        <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: '#34d399' }} />
        <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: '#34d399', animation: 'pulse 2s ease-in-out infinite' }} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 600 }}>
          {latest ? (
            <>
              {PLATFORM_ICON[latest.platform] || '•'} {latest.username ? `@${latest.username}` : 'Unknown'} — "{(latest.caption || 'untitled').slice(0, 40)}"
            </>
          ) : 'Watching for new activity…'}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          {latest ? `Latest event · ${timeAgo(latest.timestamp)}` : 'No events yet'}
        </div>
      </div>
      {seenCount > 0 && <Badge variant="emerald">{seenCount} new this session</Badge>}
    </div>
  )
}
