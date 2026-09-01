import { useState, useEffect, lazy, Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import AuthModal from '../components/auth/AuthModal'
import Reveal from '../components/motion/Reveal'
import Tilt from '../components/motion/Tilt'
import Magnetic from '../components/motion/Magnetic'

// Lazy for the same reason as the ambient field in App.jsx: the headline and
// CTAs must paint immediately, with the 3D core arriving underneath them a
// moment later rather than gating them behind a three.js download.
const HeroCore = lazy(() => import('../three/HeroCore'))

const features = [
  { icon: '🧠', title: 'Cognitive Identity', desc: 'Your digital twin learns who you are — interests, behaviors, and thinking patterns.', accent: '#818cf8' },
  { icon: '📊', title: 'Behavior Analytics', desc: 'See how you engage with content across topics, creators, and time.', accent: '#22d3ee' },
  { icon: '🔄', title: 'Real-time Pipeline', desc: 'Watch your data flow through behavior analysis, evidence, inference, and reflection.', accent: '#a78bfa' },
  { icon: '💬', title: 'AI Chat', desc: 'Ask questions about your digital self. The AI reasons from your actual cognitive data.', accent: '#f472b6' },
]

const personas = [
  {
    icon: '👤', title: 'Individuals',
    desc: 'Build your own private cognitive twin from your browsing history. Free, and your data stays yours.',
    cta: 'Create your twin', mode: 'register', accent: '#818cf8',
  },
  {
    icon: '🏢', title: 'Organizations',
    desc: 'Give every member their own private twin under one workspace with shared billing and seat management. Admins manage the roster — never member data.',
    cta: 'Set up a workspace', mode: 'register', accent: '#22d3ee',
  },
  {
    icon: '🔬', title: 'Researchers',
    desc: 'Study real digital-behavior patterns with an opt-in, de-identified export — participant IDs are salted hashes, never usernames or emails.',
    cta: 'Read the data codebook', mode: 'docs', accent: '#f472b6',
  },
]

/**
 * The seven deterministic stages a query actually runs through (pipeline
 * orchestrator order). This is the real architecture, not an illustration —
 * the Pipeline page shows the same seven with live per-stage timings.
 */
const pipelineStages = [
  { key: 'runtime', label: 'Runtime', hint: 'Load identity snapshot' },
  { key: 'planning', label: 'Planning', hint: 'Resolve intent' },
  { key: 'retrieval', label: 'Retrieval', hint: 'Gather evidence' },
  { key: 'ranking', label: 'Ranking', hint: 'Score relevance' },
  { key: 'fusion', label: 'Fusion', hint: 'Merge signals' },
  { key: 'decision', label: 'Decision', hint: 'Choose response' },
  { key: 'verbalize', label: 'Verbalize', hint: 'LLM phrasing only' },
]

const seedSteps = ['Events', 'Evidence', 'Inferences', 'Identity', 'Reflections', 'Done']

export default function LandingPage() {
  const navigate = useNavigate()
  const [demoLoading, setDemoLoading] = useState(false)
  const [demoStatus, setDemoStatus] = useState('')
  const [seedStep, setSeedStep] = useState(0)
  const [showDemoAnimation, setShowDemoAnimation] = useState(false)
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState('register')
  // Drives the travelling highlight along the pipeline diagram.
  const [activeStage, setActiveStage] = useState(0)

  const openAuth = (mode) => { setAuthMode(mode); setAuthOpen(true) }

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
        // Explicit opt-in: unauthenticated visits to inner routes redirect
        // to this landing page by default (see AppShell.jsx) — this flag is
        // what lets a signed-out demo session keep browsing past this point.
        localStorage.setItem('aim_demo_mode', 'true')
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

  // Cycles the pipeline diagram's highlight. Paused while the seeding overlay
  // is up so two animations aren't competing for attention.
  useEffect(() => {
    if (showDemoAnimation) return
    const id = setInterval(() => setActiveStage(s => (s + 1) % pipelineStages.length), 1400)
    return () => clearInterval(id)
  }, [showDemoAnimation])

  const title = 'AIMirror'

  return (
    // zIndex 1 for the same reason as AppShell's shell div — it has to claim a
    // layer above the ambient field's canvas (z-index 0). See motion.css.
    <div style={{ minHeight: '100vh', position: 'relative', zIndex: 1, overflowX: 'hidden' }}>
      {/* Sign-in entry point for returning users — the landing page has no
          sidebar to hide this in, so it needs its own visible affordance. */}
      <div style={{ position: 'fixed', top: 20, right: 24, zIndex: 20 }}>
        <Magnetic strength={0.22}>
          <button
            onClick={() => openAuth('login')}
            className="btn-3d"
            style={{
              padding: '10px 20px', borderRadius: 12,
              background: 'rgba(15,23,42,0.6)', backdropFilter: 'blur(14px)',
              WebkitBackdropFilter: 'blur(14px)',
              border: '1px solid var(--border-default)',
              color: 'var(--text-secondary)', fontSize: 13, fontWeight: 600, cursor: 'pointer',
            }}
          >
            Sign in
          </button>
        </Magnetic>
      </div>

      {/* Demo loading overlay */}
      {showDemoAnimation && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 1200,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(2,6,23,0.88)', backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          flexDirection: 'column', gap: 22,
          animation: 'fadeIn 0.3s ease-out both',
        }}>
          <div className="float-y" style={{
            width: 76, height: 76, borderRadius: 22,
            background: 'var(--accent-gradient-aurora)', backgroundSize: '220% auto',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 32,
            boxShadow: '0 0 60px -10px rgba(99,102,241,0.9)',
            animation: 'auroraSlide 5s var(--ease-glide) infinite, floatY 2.6s ease-in-out infinite',
          }}>
            ⚡
          </div>
          <div style={{ fontSize: 21, fontWeight: 700, letterSpacing: '-0.02em' }}>Setting Up Your Demo Environment</div>

          <div style={{ width: 340, maxWidth: '80vw' }}>
            <div style={{
              height: 5, borderRadius: 3,
              background: 'rgba(148,163,184,0.14)', overflow: 'hidden',
              marginBottom: 14,
            }}>
              <div style={{
                height: '100%', borderRadius: 3,
                width: `${Math.min(100, (seedStep / 6) * 100)}%`,
                background: 'var(--accent-gradient-aurora)', backgroundSize: '220% auto',
                boxShadow: '0 0 18px rgba(99,102,241,0.7)',
                transition: 'width 0.5s var(--ease-swift)',
                animation: 'auroraSlide 4s var(--ease-glide) infinite',
              }} />
            </div>
          </div>

          <div style={{ fontSize: 14, color: 'var(--text-tertiary)', minHeight: 24 }}>
            {demoStatus}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {seedSteps.map((label, i) => (
              <div
                key={label}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  opacity: i < seedStep ? 1 : 0.3,
                  transform: i === seedStep ? 'translateX(4px)' : 'none',
                  transition: 'all 0.4s var(--ease-swift)',
                  fontSize: 13, color: i < seedStep ? 'var(--text-secondary)' : 'var(--text-muted)',
                }}
              >
                <div style={{
                  width: 22, height: 22, borderRadius: 11,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, fontWeight: 700,
                  background: i < seedStep ? 'var(--emerald-500)' : i === seedStep ? 'var(--indigo-500)' : 'rgba(148,163,184,0.15)',
                  boxShadow: i === seedStep ? '0 0 14px rgba(99,102,241,0.8)' : 'none',
                  color: 'white',
                  transition: 'all 0.3s var(--ease-swift)',
                }}>
                  {i < seedStep ? '✓' : i === seedStep ? '●' : ''}
                </div>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ================================================================ HERO */}
      <section style={{
        position: 'relative',
        minHeight: 'min(94vh, 860px)',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '96px 32px 64px',
        textAlign: 'center',
      }}>
        {/* The 3D core lives behind the copy, sized to the hero band. It is
            aria-hidden and pointer-events:none, so it never sits between the
            reader and the CTAs. */}
        <Suspense fallback={null}>
          <HeroCore height={760} />
        </Suspense>

        {/* Soft coloured pools that anchor the core to the page. */}
        <div className="halo" style={{ width: 520, height: 520, top: '6%', left: '50%', marginLeft: -260, background: 'rgba(79,70,229,0.28)' }} />
        <div className="halo" style={{ width: 340, height: 340, top: '38%', left: '18%', background: 'rgba(34,211,238,0.16)', animationDelay: '1.6s' }} />
        <div className="halo" style={{ width: 300, height: 300, top: '30%', right: '16%', background: 'rgba(236,72,153,0.14)', animationDelay: '3.1s' }} />

        {/* Legibility scrim. The core renders additively, so wherever it sits
            behind the headline it lifts the background toward white and the
            copy loses contrast. This sits between the canvas (z-auto) and the
            copy (z-2) and darkens only the centre band where the text is. */}
        <div
          aria-hidden="true"
          style={{
            position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none',
            background: 'radial-gradient(ellipse 58% 40% at 50% 50%, rgba(2,6,23,0.9) 0%, rgba(2,6,23,0.74) 42%, rgba(2,6,23,0.32) 68%, transparent 84%)',
          }}
        />

        <div style={{ position: 'relative', zIndex: 2, maxWidth: 900, width: '100%' }}>
          <Reveal variant="scale">
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '6px 14px 6px 8px', borderRadius: 100, marginBottom: 28,
              background: 'rgba(15,23,42,0.55)', backdropFilter: 'blur(14px)',
              WebkitBackdropFilter: 'blur(14px)',
              border: '1px solid rgba(148,163,184,0.16)',
              fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 500,
            }}>
              <span className="pulse-dot" style={{
                width: 7, height: 7, borderRadius: '50%',
                background: 'var(--emerald-400)', color: 'var(--emerald-400)',
              }} />
              Deterministic cognitive core · the LLM only phrases the answer
            </div>
          </Reveal>

          <h1
            className="display-title title-in"
            style={{
              fontSize: 'clamp(52px, 9vw, 104px)', fontWeight: 800,
              lineHeight: 1.02, marginBottom: 20,
              '--title-delay': '150ms',
            }}
          >
            {title}
          </h1>

          <Reveal delay={620}>
            <p style={{
              fontSize: 'clamp(19px, 2.6vw, 26px)', color: 'var(--text-secondary)',
              maxWidth: 640, margin: '0 auto 14px', lineHeight: 1.45, fontWeight: 500,
            }}>
              Your Cognitive Digital Twin
            </p>
          </Reveal>

          <Reveal delay={720}>
            <p style={{
              fontSize: 16, color: 'var(--text-muted)',
              maxWidth: 560, margin: '0 auto 44px', lineHeight: 1.65,
            }}>
              Import your digital behavior, and AIMirror builds a living cognitive model — your identity, evidence, decisions, and reflections.
            </p>
          </Reveal>

          {/* CTAs */}
          <Reveal delay={820}>
            <div style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap' }}>
              <Magnetic strength={0.34}>
                <button
                  onClick={() => openAuth('register')}
                  className="btn-3d btn-aurora shine"
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '17px 36px', borderRadius: 15,
                    color: 'white', fontSize: 16, fontWeight: 700,
                    border: 'none', cursor: 'pointer',
                  }}
                >
                  Sign up free →
                </button>
              </Magnetic>

              <Magnetic strength={0.22}>
                <button
                  onClick={() => navigate('/import')}
                  className="btn-3d"
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '17px 30px', borderRadius: 15,
                    background: 'rgba(15,23,42,0.55)', backdropFilter: 'blur(14px)',
                    WebkitBackdropFilter: 'blur(14px)',
                    color: 'var(--text-primary)', fontSize: 16, fontWeight: 600,
                    border: '1px solid var(--border-strong)', cursor: 'pointer',
                  }}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
                    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
                    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>
                  </svg>
                  Import from Instagram
                </button>
              </Magnetic>

              <Magnetic strength={0.22}>
                <button
                  onClick={handleDemoData}
                  disabled={demoLoading}
                  className="btn-3d"
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '17px 30px', borderRadius: 15,
                    background: 'rgba(15,23,42,0.55)', backdropFilter: 'blur(14px)',
                    WebkitBackdropFilter: 'blur(14px)',
                    color: 'var(--text-primary)', fontSize: 16, fontWeight: 600,
                    border: '1px solid var(--border-strong)',
                    cursor: demoLoading ? 'not-allowed' : 'pointer',
                    opacity: demoLoading ? 0.6 : 1,
                  }}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                  </svg>
                  {demoLoading ? 'Loading...' : 'Load Demo Data'}
                </button>
              </Magnetic>
            </div>
          </Reveal>

          {/* Already have data */}
          <Reveal delay={900}>
            <div style={{ marginTop: 30 }}>
              <button
                onClick={() => { localStorage.setItem('aim_demo_mode', 'true'); navigate('/dashboard') }}
                style={{
                  background: 'none', border: 'none',
                  color: 'var(--text-muted)', fontSize: 14, cursor: 'pointer',
                  textDecoration: 'underline', textUnderlineOffset: 3,
                  transition: 'color var(--dur-fast) var(--ease-swift)',
                }}
                onMouseEnter={e => { e.currentTarget.style.color = 'var(--indigo-300)' }}
                onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)' }}
              >
                Already have data? Go to Dashboard →
              </button>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ========================================================= PIPELINE */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '0 32px 96px', position: 'relative', zIndex: 1 }}>
        <Reveal variant="depth">
          <div className="card card-gradient grain" style={{ padding: '36px 28px', position: 'relative', overflow: 'hidden' }}>
            <div style={{ textAlign: 'center', marginBottom: 30 }}>
              <div style={{
                fontSize: 11, fontWeight: 700, letterSpacing: '0.14em',
                textTransform: 'uppercase', color: 'var(--indigo-300)', marginBottom: 10,
              }}>
                How a question gets answered
              </div>
              <h2 style={{ fontSize: 'clamp(22px, 3vw, 30px)', fontWeight: 700, letterSpacing: '-0.02em' }}>
                Seven deterministic stages
              </h2>
            </div>

            {/* One unbroken row. It was wrapping before, which orphaned stage
                07 onto its own line and broke the left-to-right reading of a
                sequence. Fixed-width stages + nowrap keep the chain intact,
                and the strip scrolls inside itself on narrow screens rather
                than forcing the page to scroll sideways. */}
            <div style={{ overflowX: 'auto', paddingBottom: 6 }}>
              <div style={{
                display: 'flex', alignItems: 'stretch', gap: 6,
                flexWrap: 'nowrap', justifyContent: 'center',
                minWidth: 'min-content', margin: '0 auto',
              }}>
                {pipelineStages.map((stage, i) => {
                  const active = i === activeStage
                  const passed = i < activeStage
                  // Stage 7 is the only one that reaches a language model —
                  // colouring it apart from the six deterministic stages makes
                  // the product's central claim legible at a glance.
                  const isLLM = stage.key === 'verbalize'
                  const activeBg = isLLM
                    ? 'linear-gradient(150deg, rgba(236,72,153,0.28), rgba(245,158,11,0.14))'
                    : 'linear-gradient(150deg, rgba(99,102,241,0.28), rgba(34,211,238,0.14))'
                  const activeBorder = isLLM ? 'rgba(244,114,182,0.55)' : 'rgba(129,140,248,0.55)'
                  const activeGlow = isLLM
                    ? '0 0 26px -6px rgba(236,72,153,0.75)'
                    : '0 0 26px -6px rgba(99,102,241,0.75)'

                  return (
                    <div key={stage.key} style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                      <div
                        style={{
                          width: 112, padding: '14px 10px', borderRadius: 14,
                          textAlign: 'center',
                          background: active ? activeBg : 'rgba(148,163,184,0.05)',
                          border: `1px solid ${active ? activeBorder : isLLM ? 'rgba(244,114,182,0.22)' : 'rgba(148,163,184,0.12)'}`,
                          boxShadow: active ? activeGlow : 'none',
                          transform: active ? 'translateY(-4px) scale(1.04)' : 'none',
                          transition: 'all 460ms var(--ease-spring)',
                        }}
                      >
                        <div style={{
                          fontSize: 10, fontWeight: 700, letterSpacing: '0.08em',
                          color: active
                            ? (isLLM ? 'var(--pink-400)' : 'var(--cyan-400)')
                            : passed ? 'var(--emerald-400)' : 'var(--text-muted)',
                          marginBottom: 5,
                        }}>
                          {String(i + 1).padStart(2, '0')}
                        </div>
                        <div style={{
                          fontSize: 13, fontWeight: 600,
                          color: active ? 'var(--text-primary)' : 'var(--text-tertiary)',
                          marginBottom: 3,
                        }}>
                          {stage.label}
                        </div>
                        <div style={{ fontSize: 10.5, color: 'var(--text-muted)', lineHeight: 1.35 }}>
                          {stage.hint}
                        </div>
                      </div>
                      {i < pipelineStages.length - 1 && (
                        <div style={{
                          width: 14, height: 2, borderRadius: 2, flexShrink: 0,
                          background: i < activeStage ? 'var(--emerald-400)' : 'rgba(148,163,184,0.2)',
                          boxShadow: i < activeStage ? '0 0 8px rgba(52,211,153,0.7)' : 'none',
                          transition: 'all 400ms var(--ease-swift)',
                        }} />
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            <p style={{
              textAlign: 'center', fontSize: 13, color: 'var(--text-muted)',
              marginTop: 26, maxWidth: 620, marginLeft: 'auto', marginRight: 'auto', lineHeight: 1.6,
            }}>
              Stages 1–6 are pure computation over your own data — reproducible and inspectable.
              The language model is only reached at stage 7, to phrase what the pipeline already decided.
            </p>
          </div>
        </Reveal>
      </section>

      {/* ========================================================= FEATURES */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '0 32px 96px', position: 'relative', zIndex: 1 }}>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 20,
        }}>
          {features.map((f, i) => (
            <Reveal key={f.title} variant="depth" delay={i * 90}>
              <Tilt max={11} scale={1.03}>
                <div
                  className="card card-gradient spotlight"
                  style={{ padding: 28, height: '100%', borderRadius: 'var(--radius-xl)' }}
                >
                  <div className="tilt-layer" style={{ '--z': '38px' }}>
                    <div style={{
                      width: 54, height: 54, borderRadius: 16, marginBottom: 18,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 26,
                      background: `radial-gradient(circle at 30% 25%, ${f.accent}33, ${f.accent}0d)`,
                      border: `1px solid ${f.accent}3d`,
                      boxShadow: `0 8px 28px -10px ${f.accent}`,
                    }}>
                      {f.icon}
                    </div>
                    <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 9 }}>{f.title}</h3>
                    <p style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.65 }}>{f.desc}</p>
                  </div>
                </div>
              </Tilt>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ========================================================= PERSONAS */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '0 32px 110px', position: 'relative', zIndex: 1 }}>
        <Reveal>
          <h2 style={{
            textAlign: 'center', fontSize: 'clamp(24px, 3.4vw, 34px)',
            fontWeight: 700, marginBottom: 10, letterSpacing: '-0.02em',
          }}>
            Built for how you'll actually use it
          </h2>
        </Reveal>
        <Reveal delay={90}>
          <p style={{
            textAlign: 'center', color: 'var(--text-muted)', fontSize: 14.5,
            marginBottom: 44, maxWidth: 640, marginLeft: 'auto', marginRight: 'auto', lineHeight: 1.6,
          }}>
            Every account is a private, individual cognitive twin — orgs and studies are organized around that, never around sharing your data.
          </p>
        </Reveal>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(270px, 1fr))', gap: 20 }}>
          {personas.map((p, i) => (
            <Reveal key={p.title} variant="depth" delay={i * 110}>
              <Tilt max={8} scale={1.02}>
                <div
                  className="card gradient-border spotlight"
                  style={{
                    padding: 30, display: 'flex', flexDirection: 'column', height: '100%',
                    borderRadius: 'var(--radius-xl)',
                  }}
                >
                  <div className="tilt-layer" style={{ '--z': '28px', display: 'flex', flexDirection: 'column', flex: 1 }}>
                    <div style={{ fontSize: 30, marginBottom: 16 }}>{p.icon}</div>
                    <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 10 }}>{p.title}</h3>
                    <p style={{ fontSize: 13, color: 'var(--text-tertiary)', lineHeight: 1.7, flex: 1, marginBottom: 22 }}>{p.desc}</p>
                    <button
                      onClick={() => p.mode === 'docs' ? navigate('/documentation') : openAuth(p.mode)}
                      className="btn-3d"
                      style={{
                        padding: '11px 18px', borderRadius: 11, alignSelf: 'flex-start',
                        background: `${p.accent}1f`, border: `1px solid ${p.accent}45`,
                        color: p.accent, fontSize: 13, fontWeight: 600, cursor: 'pointer',
                      }}
                    >
                      {p.cta} →
                    </button>
                  </div>
                </div>
              </Tilt>
            </Reveal>
          ))}
        </div>
      </section>

      <footer style={{
        textAlign: 'center', padding: '28px 32px 40px',
        fontSize: 12, color: 'var(--text-muted)',
        borderTop: '1px solid var(--border-subtle)',
        position: 'relative', zIndex: 1,
      }}>
        AIMirror — Cognitive Digital Twin
      </footer>

      {authOpen && <AuthModal initialMode={authMode} onClose={() => setAuthOpen(false)} />}
    </div>
  )
}
