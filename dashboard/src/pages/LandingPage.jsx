import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

const features = [
  { icon: '🧠', title: 'Cognitive Identity', desc: 'Your digital twin learns who you are — interests, behaviors, and thinking patterns.' },
  { icon: '📊', title: 'Behavior Analytics', desc: 'See how you engage with content across topics, creators, and time.' },
  { icon: '🔄', title: 'Real-time Pipeline', desc: 'Watch your data flow through behavior analysis, evidence, inference, and reflection.' },
  { icon: '💬', title: 'AI Chat', desc: 'Ask questions about your digital self. The AI reasons from your actual cognitive data.' },
]

const floatingElements = [
  { emoji: '🧠', x: 15, y: 20, size: 28, delay: 0, duration: 6 },
  { emoji: '⚡', x: 80, y: 15, size: 22, delay: 1, duration: 7 },
  { emoji: '🔮', x: 70, y: 75, size: 26, delay: 2, duration: 5 },
  { emoji: '✨', x: 25, y: 80, size: 20, delay: 0.5, duration: 8 },
  { emoji: '🌐', x: 85, y: 45, size: 24, delay: 1.5, duration: 6 },
  { emoji: '💡', x: 10, y: 55, size: 22, delay: 3, duration: 7 },
]

export default function LandingPage() {
  const navigate = useNavigate()
  const [demoLoading, setDemoLoading] = useState(false)
  const [demoStatus, setDemoStatus] = useState('')
  const [seedStep, setSeedStep] = useState(0)
  const [showDemoAnimation, setShowDemoAnimation] = useState(false)

  const handleDemoData = async () => {
    setDemoLoading(true)
    setShowDemoAnimation(true)
    setSeedStep(0)

    const steps = [
      { msg: 'Generating behavioral events...', delay: 800 },
      { msg: 'Creating evidence objects...', delay: 600 },
      { msg: 'Building inferences...', delay: 700 },
      { msg: 'Constructing identity profile...', delay: 900 },
      { msg: 'Generating reflections...', delay: 500 },
      { msg: 'Seeding complete!', delay: 400 },
    ]

    try {
      for (let i = 0; i < steps.length; i++) {
        await new Promise(r => setTimeout(r, steps[i].delay))
        setSeedStep(i + 1)
        setDemoStatus(steps[i].msg)
      }

      const result = await api.seedDemo()
      if (result.success) {
        await new Promise(r => setTimeout(r, 800))
        setDemoStatus('Demo data ready! Redirecting...')
        await new Promise(r => setTimeout(r, 1000))
        navigate('/dashboard')
      }
    } catch (err) {
      setDemoStatus('Error loading demo data. Try again.')
      setDemoLoading(false)
      setShowDemoAnimation(false)
    }
  }

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  return (
    <div style={{ minHeight: '100vh', position: 'relative' }}>
      {/* Floating background elements */}
      {floatingElements.map((el, i) => (
        <div
          key={i}
          style={{
            position: 'fixed',
            left: `${el.x}%`,
            top: `${el.y}%`,
            fontSize: el.size,
            opacity: 0.15,
            pointerEvents: 'none',
            animation: `float ${el.duration}s ease-in-out ${el.delay}s infinite`,
            zIndex: 0,
          }}
        >
          {el.emoji}
        </div>
      ))}

      {/* Demo loading overlay */}
      {showDemoAnimation && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 100,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(2,6,23,0.85)', backdropFilter: 'blur(16px)',
          flexDirection: 'column', gap: 24,
          animation: 'fadeIn 0.3s ease-out both',
        }}>
          <div style={{
            width: 64, height: 64, borderRadius: 16,
            background: 'var(--accent-gradient)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 28,
            animation: 'float 2s ease-in-out infinite',
          }}>
            ⚡
          </div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>Setting Up Your Demo Environment</div>

          <div style={{ width: 320, maxWidth: '80vw' }}>
            <div style={{
              height: 4, borderRadius: 2,
              background: 'var(--border-subtle)', overflow: 'hidden',
              marginBottom: 16,
            }}>
              <div style={{
                height: '100%', borderRadius: 2,
                width: `${Math.min(100, (seedStep / 6) * 100)}%`,
                background: 'var(--accent-gradient)',
                transition: 'width 0.5s ease-out',
              }} />
            </div>
          </div>

          <div style={{ fontSize: 14, color: 'var(--text-tertiary)', minHeight: 24 }}>
            {demoStatus}
          </div>

          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              style={{
                display: 'flex', alignItems: 'center', gap: 12,
                opacity: i < seedStep ? 1 : 0.3,
                transition: 'all 0.4s ease',
                fontSize: 13, color: i < seedStep ? 'var(--text-secondary)' : 'var(--text-muted)',
              }}
            >
              <div style={{
                width: 20, height: 20, borderRadius: 10,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 10, fontWeight: 700,
                background: i < seedStep ? 'var(--emerald-500)' : i === seedStep ? 'var(--indigo-500)' : 'var(--border-subtle)',
                color: 'white',
                transition: 'all 0.3s ease',
              }}>
                {i < seedStep ? '✓' : i === seedStep ? '●' : ''}
              </div>
              <span>{['Events', 'Evidence', 'Inferences', 'Identity', 'Reflections', 'Done'][i]}</span>
            </div>
          ))}
        </div>
      )}

      {/* Hero */}
      <div style={{
        maxWidth: 900, margin: '0 auto', padding: '80px 32px 60px',
        textAlign: 'center', position: 'relative', zIndex: 1,
      }}>
        {/* Logo */}
        <div style={{
          width: 72, height: 72, borderRadius: 20,
          background: 'var(--accent-gradient)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 32, fontWeight: 800, color: 'white',
          margin: '0 auto 24px',
          boxShadow: 'var(--shadow-glow-strong)',
          animation: 'float 3s ease-in-out infinite',
        }}>
          A
        </div>

        <h1 style={{
          fontSize: 56, fontWeight: 800, letterSpacing: '-0.04em',
          lineHeight: 1.15, marginBottom: 16,
        }}>
          <span className="gradient-text">AIMirror</span>
        </h1>
        <p style={{
          fontSize: 22, color: 'var(--text-tertiary)',
          maxWidth: 600, margin: '0 auto 48px',
          lineHeight: 1.5,
        }}>
          Your Cognitive Digital Twin
        </p>
        <p style={{
          fontSize: 16, color: 'var(--text-muted)',
          maxWidth: 520, margin: '-32px auto 48px',
          lineHeight: 1.6,
        }}>
          Import your digital behavior, and AIMirror builds a living cognitive model — your identity, evidence, decisions, and reflections.
        </p>

        {/* CTAs */}
        <div style={{
          display: 'flex', gap: 16, justifyContent: 'center',
          flexWrap: 'wrap',
        }}>
          <button
            onClick={() => navigate('/import')}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '16px 32px', borderRadius: 14,
              background: 'var(--accent-gradient)',
              color: 'white', fontSize: 16, fontWeight: 600,
              border: 'none', cursor: 'pointer',
              boxShadow: 'var(--shadow-glow)',
              transition: 'all 0.3s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = 'var(--shadow-glow-strong)' }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'var(--shadow-glow)' }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
              <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
              <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>
            </svg>
            Import from Instagram
          </button>

          <button
            onClick={handleDemoData}
            disabled={demoLoading}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '16px 32px', borderRadius: 14,
              background: 'transparent',
              color: 'var(--text-primary)', fontSize: 16, fontWeight: 600,
              border: '1px solid var(--border-strong)',
              cursor: demoLoading ? 'not-allowed' : 'pointer',
              opacity: demoLoading ? 0.6 : 1,
              transition: 'all 0.3s ease',
            }}
            onMouseEnter={e => { if (!demoLoading) { e.currentTarget.style.background = 'var(--bg-surface)'; e.currentTarget.style.borderColor = 'var(--accent)' }}}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'var(--border-strong)' }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
            {demoLoading ? 'Loading...' : 'Load Demo Data'}
          </button>
        </div>

        {/* Already have data */}
        <div style={{ marginTop: 32 }}>
          <button
            onClick={() => navigate('/dashboard')}
            style={{
              background: 'none', border: 'none',
              color: 'var(--text-muted)', fontSize: 14, cursor: 'pointer',
              textDecoration: 'underline',
              textUnderlineOffset: 3,
            }}
          >
            Already have data? Go to Dashboard →
          </button>
        </div>
      </div>

      {/* Features grid */}
      <div style={{
        maxWidth: 1000, margin: '0 auto', padding: '0 32px 80px',
        position: 'relative', zIndex: 1,
      }}>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: 20,
        }}>
          {features.map((f, i) => (
            <div
              key={i}
              className="card card-gradient"
              style={{
                padding: 28,
                animation: `fadeIn 0.5s ease-out ${i * 0.1}s both`,
              }}
            >
              <div style={{ fontSize: 32, marginBottom: 16 }}>{f.icon}</div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>{f.title}</h3>
              <p style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.6 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
