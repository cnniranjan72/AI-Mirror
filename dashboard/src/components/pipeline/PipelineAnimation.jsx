import { useEffect, useRef } from 'react'
import GlassCard from '../ui/GlassCard'

export default function PipelineAnimation({ currentPhase, phases }) {
  const activePhase = phases[currentPhase] || phases[phases.length - 1]
  const progress = ((currentPhase + 1) / phases.length) * 100
  const containerRef = useRef(null)

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.querySelector(`[data-phase="${currentPhase}"]`)?.scrollIntoView({
        behavior: 'smooth', block: 'center',
      })
    }
  }, [currentPhase])

  return (
    <GlassCard gradient padding="2xl">
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 6 }}>
          Processing Cognitive Pipeline
        </h2>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 14 }}>
          Building your cognitive profile in real-time
        </p>
      </div>

      {/* Overall progress */}
      <div style={{ marginBottom: 28 }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          fontSize: 13, color: 'var(--text-muted)', marginBottom: 8,
        }}>
          <span>Pipeline Progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div style={{
          height: 6, borderRadius: 3,
          background: 'var(--border-subtle)', overflow: 'hidden',
        }}>
          <div style={{
            height: '100%', borderRadius: 3,
            width: `${progress}%`,
            background: 'var(--accent-gradient)',
            transition: 'width 0.5s ease-out',
          }} />
        </div>
      </div>

      {/* Active phase indicator */}
      <div style={{
        padding: '16px 20px', borderRadius: 12,
        background: 'rgba(99,102,241,0.1)',
        border: '1px solid rgba(99,102,241,0.2)',
        marginBottom: 24,
        display: 'flex', alignItems: 'center', gap: 16,
      }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10,
          background: 'var(--accent-gradient)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 18,
          animation: 'pulse 2s ease-in-out infinite',
        }}>
          ⚡
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--indigo-400)' }}>
            {activePhase?.label}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
            Phase {currentPhase + 1} of {phases.length}
          </div>
        </div>
        <div style={{
          fontSize: 12, color: 'var(--text-muted)',
          fontFamily: 'var(--font-mono)',
        }}>
          {activePhase?.duration ? `${(activePhase.duration / 1000).toFixed(1)}s` : '--'}
        </div>
      </div>

      {/* Pipeline stages */}
      <div
        ref={containerRef}
        style={{
          display: 'flex', flexDirection: 'column', gap: 4,
          maxHeight: 340, overflowY: 'auto',
          paddingRight: 8,
        }}
      >
        {phases.map((phase, i) => {
          const isComplete = i < currentPhase
          const isActive = i === currentPhase
          const isPending = i > currentPhase

          return (
            <div
              key={phase.key}
              data-phase={i}
              style={{
                display: 'flex', alignItems: 'center', gap: 14,
                padding: '12px 16px', borderRadius: 10,
                background: isActive ? 'rgba(99,102,241,0.08)' : 'transparent',
                border: `1px solid ${
                  isActive ? 'rgba(99,102,241,0.2)' :
                  isComplete ? 'rgba(16,185,129,0.15)' :
                  'var(--border-subtle)'
                }`,
                opacity: isPending ? 0.4 : 1,
                transition: 'all 0.4s ease',
              }}
            >
              {/* Status icon */}
              <div style={{
                width: 28, height: 28, borderRadius: 14,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 700, flexShrink: 0,
                background: isComplete ? 'var(--emerald-500)' :
                            isActive ? 'var(--indigo-500)' :
                            'var(--border-subtle)',
                color: 'white',
                transition: 'all 0.3s ease',
              }}>
                {isComplete ? '✓' : isActive ? '●' : i + 1}
              </div>

              {/* Phase label */}
              <div style={{ flex: 1 }}>
                <div style={{
                  fontSize: 13, fontWeight: isActive ? 600 : 500,
                  color: isComplete ? 'var(--text-secondary)' :
                         isActive ? 'var(--text-primary)' :
                         'var(--text-muted)',
                }}>
                  {phase.label}
                </div>
              </div>

              {/* Timing */}
              <div style={{
                fontSize: 11, color: 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
                minWidth: 36, textAlign: 'right',
              }}>
                {isComplete && phase.duration ? `${(phase.duration / 1000).toFixed(1)}s` : ''}
              </div>

              {/* Active pulse */}
              {isActive && (
                <div style={{
                  width: 8, height: 8, borderRadius: 4,
                  background: 'var(--indigo-500)',
                  animation: 'pulse 1.5s ease-in-out infinite',
                  flexShrink: 0,
                }} />
              )}
            </div>
          )
        })}
      </div>

      {/* Pipeline flow arrow decoration */}
      <div style={{
        display: 'flex', justifyContent: 'center',
        marginTop: 16, gap: 8,
        opacity: 0.3,
      }}>
        {['📥', '→', '⚙️', '→', '🧠', '→', '✨'].map((s, i) => (
          <span key={i} style={{ fontSize: 16 }}>{s}</span>
        ))}
      </div>
    </GlassCard>
  )
}
