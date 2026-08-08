import { useState, useEffect } from 'react'
import { api, isAuthed } from '../../api/client'

/**
 * Shown once right after a successful login/register (flag set by
 * AuthModal.jsx) if the user hasn't configured an AI provider key yet.
 * Dismissible; never reappears once cleared for this login.
 */
export default function SetupToast() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!isAuthed() || sessionStorage.getItem('aim_show_setup_prompt') !== 'true') return
    sessionStorage.removeItem('aim_show_setup_prompt')
    api.getLlmSettings()
      .then(s => { if (!s.has_key && s.provider !== 'ollama') setVisible(true) })
      .catch(() => {})
  }, [])

  if (!visible) return null

  return (
    <div
      className="animate-slide"
      style={{
        position: 'fixed', bottom: 24, right: 24, zIndex: 500,
        width: 360, maxWidth: 'calc(100vw - 48px)',
        padding: 18, borderRadius: 14,
        background: 'var(--bg-secondary, #0f172a)',
        border: '1px solid rgba(99,102,241,0.3)',
        boxShadow: 'var(--shadow-xl), var(--shadow-glow)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 10 }}>
        <div style={{ fontSize: 14, fontWeight: 700 }}>Finish setting up AIMirror</div>
        <button
          onClick={() => setVisible(false)}
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16, lineHeight: 1 }}
        >
          ×
        </button>
      </div>
      <p style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.6, marginBottom: 14 }}>
        Two things to get the most out of your twin: bring your own AI provider key, and install the
        Chrome extension so your browsing actually feeds it.
      </p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <a href="/settings" style={{
          padding: '8px 14px', borderRadius: 8, background: 'var(--accent-gradient)',
          color: 'white', fontSize: 12.5, fontWeight: 600, textDecoration: 'none',
        }}>
          Set up AI provider →
        </a>
        <a href="/documentation" style={{
          padding: '8px 14px', borderRadius: 8, border: '1px solid var(--border-subtle)',
          color: 'var(--text-secondary)', fontSize: 12.5, fontWeight: 600, textDecoration: 'none',
        }}>
          Install the extension →
        </a>
      </div>
    </div>
  )
}
