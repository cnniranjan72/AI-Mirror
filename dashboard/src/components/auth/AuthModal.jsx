import { useState } from 'react'
import { api } from '../../api/client'

export default function AuthModal({ onClose, initialMode = 'login' }) {
  const [mode, setMode] = useState(initialMode)  // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(null); setBusy(true)
    try {
      if (mode === 'register') {
        await api.register(username, password, displayName || username)
      } else {
        await api.login(username, password)
      }
      // Reload so every hook re-fetches against the now-authenticated user.
      window.location.href = '/dashboard'
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Something went wrong')
      setBusy(false)
    }
  }

  const input = {
    width: '100%', padding: '10px 12px', borderRadius: 8, marginBottom: 12,
    background: '#1e293b', border: '1px solid var(--border-strong, rgba(148,163,184,0.25))',
    color: '#f8fafc', fontSize: 14, outline: 'none', colorScheme: 'dark',
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(2,6,23,0.7)',
        backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 380, maxWidth: '90vw', padding: 28, borderRadius: 16,
          background: 'var(--bg-secondary, #0f172a)', border: '1px solid var(--border-strong, rgba(148,163,184,0.2))',
          boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
        }}
      >
        <h2 className="gradient-text" style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>
          {mode === 'login' ? 'Welcome back' : 'Create your twin'}
        </h2>
        <p style={{ fontSize: 13, color: 'var(--text-tertiary)', marginBottom: 20 }}>
          {mode === 'login'
            ? 'Sign in to see your own cognitive twin.'
            : 'Register to build a private twin from your own data.'}
        </p>

        <form onSubmit={submit}>
          {mode === 'register' && (
            <input style={input} placeholder="Display name (optional)" value={displayName}
              onChange={(e) => setDisplayName(e.target.value)} />
          )}
          <input style={input} placeholder="Username" value={username} autoFocus
            onChange={(e) => setUsername(e.target.value)} />
          <input style={input} type="password" placeholder="Password" value={password}
            onChange={(e) => setPassword(e.target.value)} />

          {error && <div style={{ fontSize: 13, color: '#fb7185', marginBottom: 12 }}>{error}</div>}

          <button type="submit" disabled={busy}
            style={{
              width: '100%', padding: '11px', borderRadius: 8, border: 'none',
              background: busy ? 'rgba(148,163,184,0.2)' : 'var(--accent-gradient)',
              color: 'white', fontSize: 14, fontWeight: 600, cursor: busy ? 'wait' : 'pointer',
            }}
          >
            {busy ? 'Please wait…' : (mode === 'login' ? 'Sign in' : 'Create account')}
          </button>
        </form>

        <div style={{ marginTop: 16, textAlign: 'center', fontSize: 13, color: 'var(--text-tertiary)' }}>
          {mode === 'login' ? "No account yet? " : 'Already have one? '}
          <button
            onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(null) }}
            style={{ background: 'none', border: 'none', color: '#818cf8', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}
          >
            {mode === 'login' ? 'Register' : 'Sign in'}
          </button>
        </div>

        <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <button onClick={onClose}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}>
            Continue as demo
          </button>
        </div>
      </div>
    </div>
  )
}
