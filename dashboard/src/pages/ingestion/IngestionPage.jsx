import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import GlassCard from '../../components/ui/GlassCard'
import { CheckIcon, XIcon, RefreshIcon } from '../../icons/icons'
import PipelineAnimation from '../../components/pipeline/PipelineAnimation'

const STEPS = ['Connect', 'Import Content', 'Analyze', 'Complete']

const SOURCES = [
  { id: 'posts', label: 'Posts', icon: '📷', desc: 'Photos and carousels you\'ve shared' },
  { id: 'reels', label: 'Reels', icon: '🎬', desc: 'Short-form video content' },
  { id: 'likes', label: 'Likes', icon: '❤️', desc: 'Content you\'ve engaged with' },
  { id: 'saves', label: 'Saves', icon: '🔖', desc: 'Bookmarked posts and reels' },
]

const IMPORT_PHASES = [
  { key: 'collecting', label: 'Collecting behavioral data', duration: 2000 },
  { key: 'normalizing', label: 'Normalizing events', duration: 1500 },
  { key: 'behavior_gateway', label: 'Behavior Gateway', duration: 1800 },
  { key: 'knowledge', label: 'Knowledge Consolidation', duration: 2200 },
  { key: 'behavior_objects', label: 'Building Behavior Objects', duration: 2000 },
  { key: 'evidence', label: 'Generating Evidence', duration: 2500 },
  { key: 'inference', label: 'Running Inferences', duration: 2000 },
  { key: 'reflection', label: 'Generating Reflections', duration: 1800 },
  { key: 'identity', label: 'Building Identity Profile', duration: 2500 },
  { key: 'snapshot', label: 'Taking Identity Snapshot', duration: 1500 },
  { key: 'complete', label: 'Complete!', duration: 1000 },
]

export default function IngestionPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [selectedSources, setSelectedSources] = useState(['posts', 'reels', 'likes', 'saves'])
  const [importProgress, setImportProgress] = useState(0)
  const [collectProgress, setCollectProgress] = useState(0)
  const [pipelinePhase, setPipelinePhase] = useState(0)
  const [importing, setImporting] = useState(false)
  const [complete, setComplete] = useState(false)
  const [collectCounts, setCollectCounts] = useState({})
  const [error, setError] = useState(null)
  const animRef = useRef(null)

  const toggleSource = (id) => {
    setSelectedSources(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    )
  }

  const startImport = async () => {
    setError(null)
    setImporting(true)
    setStep(2)

    try {
      // Phase 1: Collect progress
      setStep(2)
      for (let i = 0; i <= 100; i += 5) {
        await new Promise(r => setTimeout(r, 80 + Math.random() * 60))
        setCollectProgress(i)
        setCollectCounts({
          posts: Math.round(i * 2.5),
          reels: Math.round(i * 3.2),
          likes: Math.round(i * 5),
          saves: Math.round(i * 1.2),
        })
      }

      // Phase 2: Pipeline processing
      setStep(3)
      for (let i = 0; i < IMPORT_PHASES.length; i++) {
        setPipelinePhase(i)
        await new Promise(r => setTimeout(r, IMPORT_PHASES[i].duration))
      }

      setComplete(true)
      setStep(4)

      await new Promise(r => setTimeout(r, 2500))
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Import failed. Please try again.')
      setImporting(false)
    }
  }

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  return (
    <div style={{ minHeight: '100vh', padding: '40px 32px', maxWidth: 800, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 40, textAlign: 'center' }}>
        <h1 className="gradient-text" style={{ fontSize: 36, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 8 }}>
          Import Your Digital Self
        </h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15 }}>
          Connect your Instagram data to build your cognitive twin
        </p>
      </div>

      {/* Step indicator */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 0, marginBottom: 40,
      }}>
        {STEPS.map((s, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center' }}>
            {i > 0 && (
              <div style={{
                width: 40, height: 2,
                background: i <= step ? 'var(--accent-gradient)' : 'var(--border-subtle)',
                transition: 'background 0.5s ease',
              }} />
            )}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '8px 16px', borderRadius: 20,
              background: i <= step ? 'rgba(99,102,241,0.15)' : 'transparent',
              border: `1px solid ${i <= step ? 'rgba(99,102,241,0.3)' : 'var(--border-subtle)'}`,
              transition: 'all 0.3s ease',
            }}>
              <div style={{
                width: 24, height: 24, borderRadius: 12,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 700,
                background: i < step ? 'var(--emerald-500)' : i === step ? 'var(--accent-gradient)' : 'var(--border-subtle)',
                color: 'white',
              }}>
                {i < step ? '✓' : i + 1}
              </div>
              <span style={{
                fontSize: 13, fontWeight: 500,
                color: i <= step ? 'var(--text-primary)' : 'var(--text-muted)',
              }}>
                {s}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Step 0: Connect */}
      {step === 0 && (
        <GlassCard gradient padding="2xl">
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{
              width: 80, height: 80, borderRadius: 24,
              background: 'linear-gradient(135deg, #f58529, #dd2a7b, #8134af, #515bd4)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 36, margin: '0 auto 24px',
              boxShadow: '0 0 40px rgba(221,42,123,0.3)',
            }}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="white">
                <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
                <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
                <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>
              </svg>
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Connect Instagram</h2>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 14, maxWidth: 400, margin: '0 auto 32px', lineHeight: 1.6 }}>
              AIMirror will analyze your Instagram activity to build your cognitive profile.
              Your data stays private and is processed locally.
            </p>

            <div style={{
              background: 'rgba(0,0,0,0.2)', borderRadius: 12, padding: 20,
              marginBottom: 24, textAlign: 'left', fontSize: 13,
              color: 'var(--text-tertiary)', lineHeight: 1.6,
            }}>
              <div style={{ fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>What happens next:</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[
                  'AIMirror scans your selected Instagram data sources',
                  'Events are normalized and analyzed through the cognitive pipeline',
                  'Your identity profile is generated from patterns in your behavior',
                  'You can explore your cognitive data through the dashboard',
                ].map((item, i) => (
                  <div key={i} style={{ display: 'flex', gap: 8 }}>
                    <span style={{ color: 'var(--indigo-400)' }}>→</span>
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() => setStep(1)}
              className="card card-gradient"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 10,
                padding: '16px 40px', borderRadius: 14,
                background: 'linear-gradient(135deg, #f58529, #dd2a7b, #8134af)',
                color: 'white', fontSize: 16, fontWeight: 600,
                border: 'none', cursor: 'pointer',
                boxShadow: '0 4px 20px rgba(221,42,123,0.4)',
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
                <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
                <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>
              </svg>
              Connect Instagram Account
            </button>

            <div style={{ marginTop: 16 }}>
              <button
                onClick={() => navigate('/')}
                style={{
                  background: 'none', border: 'none',
                  color: 'var(--text-muted)', fontSize: 13, cursor: 'pointer',
                  textDecoration: 'underline',
                }}
              >
                Skip — try demo data instead
              </button>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Step 1: Select data sources */}
      {step === 1 && (
        <div style={{ animation: 'fadeIn 0.4s ease-out both' }}>
          <GlassCard gradient padding="2xl">
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 6 }}>Select Data Sources</h2>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 14, marginBottom: 24 }}>
              Choose what to import from your Instagram account
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {SOURCES.map(source => {
                const selected = selectedSources.includes(source.id)
                return (
                  <button
                    key={source.id}
                    onClick={() => toggleSource(source.id)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 16,
                      padding: '16px 20px', borderRadius: 12,
                      background: selected ? 'rgba(99,102,241,0.1)' : 'rgba(0,0,0,0.2)',
                      border: `1px solid ${selected ? 'rgba(99,102,241,0.3)' : 'var(--border-subtle)'}`,
                      cursor: 'pointer', textAlign: 'left',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <div style={{
                      width: 44, height: 44, borderRadius: 12,
                      background: selected ? 'rgba(99,102,241,0.15)' : 'rgba(148,163,184,0.1)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 22, flexShrink: 0,
                    }}>
                      {source.icon}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 15, fontWeight: 600, color: selected ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                        {source.label}
                      </div>
                      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>{source.desc}</div>
                    </div>
                    <div style={{
                      width: 24, height: 24, borderRadius: 12,
                      border: `2px solid ${selected ? 'var(--indigo-500)' : 'var(--border-strong)'}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      transition: 'all 0.2s ease',
                      background: selected ? 'var(--indigo-500)' : 'transparent',
                    }}>
                      {selected && <CheckIcon />}
                    </div>
                  </button>
                )
              })}
            </div>

            <div style={{
              display: 'flex', gap: 12, justifyContent: 'center',
              marginTop: 28,
            }}>
              <button
                onClick={() => setStep(0)}
                style={{
                  padding: '12px 24px', borderRadius: 10,
                  background: 'transparent', border: '1px solid var(--border-subtle)',
                  color: 'var(--text-tertiary)', fontSize: 14, cursor: 'pointer',
                }}
              >
                Back
              </button>
              <button
                onClick={startImport}
                disabled={selectedSources.length === 0}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '12px 32px', borderRadius: 10,
                  background: selectedSources.length > 0 ? 'var(--accent-gradient)' : 'var(--border-subtle)',
                  border: 'none',
                  color: selectedSources.length > 0 ? 'white' : 'var(--text-muted)',
                  fontSize: 14, fontWeight: 600, cursor: selectedSources.length > 0 ? 'pointer' : 'not-allowed',
                  boxShadow: selectedSources.length > 0 ? 'var(--shadow-glow)' : 'none',
                }}
              >
                Import {selectedSources.length} Source{selectedSources.length > 1 ? 's' : ''}
              </button>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Step 2: Import progress */}
      {step === 2 && !complete && (
        <div style={{ animation: 'fadeIn 0.4s ease-out both' }}>
          <GlassCard gradient padding="2xl">
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 6 }}>Collecting Your Data</h2>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 14, marginBottom: 24 }}>
              Scanning and normalizing Instagram activity...
            </p>

            {/* Progress bar */}
            <div style={{ marginBottom: 28 }}>
              <div style={{
                height: 6, borderRadius: 3,
                background: 'var(--border-subtle)', overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%', borderRadius: 3,
                  width: `${collectProgress}%`,
                  background: 'var(--accent-gradient)',
                  transition: 'width 0.3s ease-out',
                }} />
              </div>
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                marginTop: 8, fontSize: 12, color: 'var(--text-muted)',
              }}>
                <span>{collectProgress}%</span>
                <span>{Math.round(collectProgress * 0.12)} items found</span>
              </div>
            </div>

            {/* Live counts */}
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
              gap: 12,
            }}>
              {SOURCES.map(s => (
                <div key={s.id} style={{
                  padding: 16, borderRadius: 10,
                  background: 'rgba(0,0,0,0.2)',
                  border: '1px solid var(--border-subtle)',
                  opacity: selectedSources.includes(s.id) ? 1 : 0.3,
                }}>
                  <div style={{ fontSize: 24, marginBottom: 8 }}>{s.icon}</div>
                  <div style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>{s.label}</div>
                  <div style={{ fontSize: 22, fontWeight: 700, marginTop: 4 }}>
                    {collectCounts[s.id] || 0}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      )}

      {/* Step 3: Pipeline processing */}
      {step === 3 && !complete && (
        <div style={{ animation: 'fadeIn 0.4s ease-out both' }}>
          <PipelineAnimation
            currentPhase={pipelinePhase}
            phases={IMPORT_PHASES}
          />
        </div>
      )}

      {/* Step 4: Complete */}
      {complete && (
        <div style={{ animation: 'scaleIn 0.5s ease-out both', textAlign: 'center' }}>
          <GlassCard gradient padding="2xl">
            <div style={{
              width: 80, height: 80, borderRadius: 40,
              background: 'var(--emerald-500)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 20px',
              fontSize: 36,
              boxShadow: '0 0 40px rgba(16,185,129,0.3)',
              animation: 'scaleIn 0.5s ease-out 0.2s both',
            }}>
              ✓
            </div>
            <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>
              Your Cognitive Twin is Ready
            </h2>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 15, maxWidth: 400, margin: '0 auto 32px' }}>
              We've analyzed your behavioral data and built your cognitive profile.
              Redirecting to your dashboard...
            </p>

            <div style={{
              display: 'flex', justifyContent: 'center', gap: 16,
            }}>
              {['Identity', 'Evidence', 'Decisions', 'Chat'].map((item, i) => (
                <div key={i} style={{
                  padding: '12px 20px', borderRadius: 10,
                  background: 'rgba(99,102,241,0.1)',
                  border: '1px solid rgba(99,102,241,0.2)',
                  fontSize: 13, fontWeight: 500,
                  color: 'var(--indigo-400)',
                  animation: `fadeIn 0.4s ease-out ${0.5 + i * 0.1}s both`,
                }}>
                  {item}
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  )
}
