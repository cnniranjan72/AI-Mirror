import { useState, useEffect } from 'react'
import { api } from '../../api/client'

/**
 * A persistent notice while collection is paused.
 *
 * The switch itself lives in Settings, but the state cannot only live there.
 * Someone who pauses collection and forgets is in the same position as someone
 * who believes a tracker is off while it is on — wrong about what the system
 * is doing to them, which is the failure this product exists to complain
 * about. So the paused state follows them across every page, and offers the
 * way back.
 *
 * Deliberately silent while collecting. A banner that is always present stops
 * being read, and there is nothing to warn about in the normal case.
 */
export default function CollectionBanner() {
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let alive = true
    const load = () => api.getCollectionStatus()
      .then(s => { if (alive) setStatus(s) })
      .catch(() => { if (alive) setStatus(null) })
    load()
    // The switch can be thrown from another tab or device, so re-check when
    // this one regains focus rather than trusting a value fetched at mount.
    const onFocus = () => load()
    window.addEventListener('focus', onFocus)
    return () => { alive = false; window.removeEventListener('focus', onFocus) }
  }, [])

  const resume = async () => {
    setBusy(true)
    try {
      setStatus(await api.setCollectionPaused(false))
    } catch {
      // Leave the banner up: failing to resume must not look like success.
    } finally {
      setBusy(false)
    }
  }

  if (!status?.paused) return null

  return (
    <div
      role="status"
      style={{
        position: 'sticky', top: 0, zIndex: 95,
        display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
        padding: '9px 18px',
        background: 'rgba(251,191,36,0.12)',
        borderBottom: '1px solid rgba(251,191,36,0.28)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        fontSize: 13, color: 'var(--text-secondary)',
      }}
    >
      <span aria-hidden="true" style={{ color: '#fbbf24' }}>&#9208;</span>
      <span>
        <strong style={{ color: '#fbbf24' }}>Collection is paused.</strong>{' '}
        New activity is not being recorded
        {status.paused_at && ` since ${new Date(status.paused_at).toLocaleDateString()}`}.
        Everything collected before then is still stored.
      </span>
      <button
        onClick={resume}
        disabled={busy}
        style={{
          marginLeft: 'auto',
          padding: '5px 12px', borderRadius: 8, fontSize: 12, fontWeight: 600,
          border: '1px solid rgba(16,185,129,0.35)',
          background: 'rgba(16,185,129,0.12)', color: '#34d399',
          cursor: busy ? 'wait' : 'pointer',
        }}
      >
        {busy ? 'Resuming…' : 'Resume'}
      </button>
    </div>
  )
}
