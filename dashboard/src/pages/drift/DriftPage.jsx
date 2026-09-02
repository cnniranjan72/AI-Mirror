import { useState, useMemo, useEffect } from 'react'
import { api } from '../../api/client'
import { useApi } from '../../hooks/useApi'
import GlassCard from '../../components/ui/GlassCard'
import Badge from '../../components/ui/Badge'
import AsyncState from '../../components/ui/AsyncState'
import Reveal from '../../components/motion/Reveal'
import { useReducedMotion } from '../../hooks/useMotion'
import { CompassIcon } from '../../icons/icons'

/**
 * Identity Drift — the seventeen measures the system keeps about you, and how
 * they moved.
 *
 * The architecture has always stored immutable versioned snapshots and measured
 * the distance between them. That number lived in a log line and was never
 * shown to the person it describes, which is a strange omission for a product
 * whose argument is that people should be able to see what is being built out
 * of their behaviour.
 *
 * Drawn as raw SVG rather than a charting library: seventeen axes on a shared
 * scale is a simple polygon, and pulling in a dependency to draw it would cost
 * more than it saves. The morph between snapshots is a CSS transition on the
 * points attribute, which browsers interpolate when the vertex count matches —
 * it always does here, since every point has the same seventeen dimensions.
 */

const SIZE = 300
const CENTRE = SIZE / 2
const RADIUS = SIZE / 2 - 34

function polygon(values, radius = RADIUS) {
  const n = values.length
  return values.map((v, i) => {
    // Start at twelve o'clock so the first axis reads as the top.
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2
    const r = radius * Math.max(0, Math.min(1, v))
    return `${CENTRE + r * Math.cos(angle)},${CENTRE + r * Math.sin(angle)}`
  }).join(' ')
}

function axisEnd(i, n, radius = RADIUS) {
  const angle = (Math.PI * 2 * i) / n - Math.PI / 2
  return { x: CENTRE + radius * Math.cos(angle), y: CENTRE + radius * Math.sin(angle) }
}

export default function DriftPage() {
  const { data, loading, error, refetch } = useApi(() => api.getIdentityDrift(), [])
  const [index, setIndex] = useState(0)
  const [hover, setHover] = useState(null)
  const reduced = useReducedMotion()

  const points = data?.points || []
  const dims = data?.dimensions || []

  // Land on the most recent point once the data arrives, since "where am I
  // now" is the question people open this with.
  useEffect(() => {
    if (points.length) setIndex(points.length - 1)
  }, [points.length])

  const current = points[index]
  const first = points[0]
  const totalShift = useMemo(() => {
    if (points.length < 2) return null
    const a = points[0].values, b = points[points.length - 1].values
    return Math.sqrt(a.reduce((s, v, i) => s + (v - b[i]) ** 2, 0))
  }, [points])

  return (
    <div>
      <div style={{ marginBottom: 26 }}>
        <h1 className="gradient-text" style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
          Identity Drift
        </h1>
        <p style={{ color: 'var(--text-tertiary)', fontSize: 15, maxWidth: 720 }}>
          The seventeen measures this system keeps about you, and how far each has moved.
          The distance between two shapes is the same figure it uses to decide a new
          snapshot is warranted.
        </p>
      </div>

      <AsyncState loading={loading} error={error} onRetry={refetch}>
        {!data?.measurable ? (
          <GlassCard gradient>
            <Badge variant="slate">Not enough history</Badge>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 10, lineHeight: 1.6 }}>
              {data?.note}
            </p>
          </GlassCard>
        ) : (
          <>
            <Reveal>
              <GlassCard gradient style={{ marginBottom: 22 }}>
                <div style={{ display: 'flex', gap: 26, flexWrap: 'wrap', alignItems: 'center' }}>
                  <div style={{ position: 'relative' }}>
                    <svg width={SIZE} height={SIZE} role="img"
                         aria-label="Radar chart of seventeen identity measures">
                      {/* Rings, so a shape can be read against a scale rather
                          than only against the other shape. */}
                      {[0.25, 0.5, 0.75, 1].map(r => (
                        <circle key={r} cx={CENTRE} cy={CENTRE} r={RADIUS * r}
                                fill="none" stroke="rgba(148,163,184,0.14)" strokeWidth="1" />
                      ))}
                      {dims.map((d, i) => {
                        const e = axisEnd(i, dims.length)
                        return (
                          <line key={d.name} x1={CENTRE} y1={CENTRE} x2={e.x} y2={e.y}
                                stroke={hover === i ? 'rgba(129,140,248,0.75)' : 'rgba(148,163,184,0.14)'}
                                strokeWidth={hover === i ? 1.6 : 1} />
                        )
                      })}

                      {/* The starting shape stays on screen as a ghost, so the
                          comparison is visible without relying on memory. */}
                      {first && first !== current && (
                        <polygon points={polygon(first.values)}
                                 fill="rgba(148,163,184,0.10)"
                                 stroke="rgba(148,163,184,0.45)"
                                 strokeWidth="1" strokeDasharray="3 3" />
                      )}

                      <polygon
                        points={polygon(current.values)}
                        fill="rgba(99,102,241,0.22)"
                        stroke="rgba(129,140,248,0.95)"
                        strokeWidth="2"
                        style={reduced ? undefined : { transition: 'points 600ms cubic-bezier(0.16,1,0.3,1)' }}
                      />

                      {dims.map((d, i) => {
                        const e = axisEnd(i, dims.length, RADIUS + 14)
                        return (
                          <circle key={d.name} cx={axisEnd(i, dims.length, RADIUS * current.values[i]).x}
                                  cy={axisEnd(i, dims.length, RADIUS * current.values[i]).y}
                                  r={hover === i ? 4 : 2.5}
                                  fill={hover === i ? '#a5b4fc' : 'rgba(129,140,248,0.8)'}
                                  onMouseEnter={() => setHover(i)}
                                  onMouseLeave={() => setHover(null)}
                                  style={{ cursor: 'pointer' }} />
                        )
                      })}
                    </svg>
                  </div>

                  <div style={{ flex: '1 1 260px', minWidth: 0 }}>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
                      showing
                    </div>
                    <div style={{ fontSize: 26, fontWeight: 800, marginBottom: 2 }}>
                      {current.label}
                      {current.kind === 'live' && (
                        <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)' }}>
                          {' '}· live identity
                        </span>
                      )}
                    </div>
                    {current.at && (
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
                        {new Date(current.at).toLocaleString()}
                      </div>
                    )}

                    <input
                      type="range" min={0} max={points.length - 1} value={index}
                      onChange={e => setIndex(Number(e.target.value))}
                      aria-label="Move through identity snapshots"
                      style={{ width: '100%', marginBottom: 6 }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
                      <span>{points[0].label}</span>
                      <span>{points[points.length - 1].label}</span>
                    </div>

                    {totalShift !== null && (
                      <div style={{ marginTop: 16, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                        Total movement from {points[0].label} to {points[points.length - 1].label}:{' '}
                        <strong style={{ color: '#a5b4fc' }}>{totalShift.toFixed(3)}</strong>
                        <span style={{ color: 'var(--text-muted)' }}>
                          {' '}of a possible {data.max_possible_shift}
                        </span>
                      </div>
                    )}
                    {hover !== null && dims[hover] && (
                      <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-tertiary)' }}>
                        <strong style={{ color: 'var(--text-secondary)' }}>{dims[hover].name}</strong>
                        {' — '}{dims[hover].meaning}
                        {' · '}now {current.values[hover].toFixed(2)}
                      </div>
                    )}
                  </div>
                </div>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 16, lineHeight: 1.6 }}>
                  {data.note}
                </p>
              </GlassCard>
            </Reveal>

            {data.biggest_moves?.length > 0 && (
              <Reveal delay={0.05}>
                <GlassCard>
                  <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>What moved most</h3>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
                    Between {points[0].label} and {points[points.length - 1].label}.
                  </p>
                  {data.biggest_moves.map(m => (
                    <div key={m.dimension} style={{
                      display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
                      padding: '10px 0', borderTop: '1px solid var(--border-subtle)',
                    }}>
                      <div style={{ flex: '1 1 240px', minWidth: 0 }}>
                        <div style={{ fontSize: 14, fontWeight: 600 }}>{m.dimension}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{m.meaning}</div>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                        {m.from.toFixed(2)} → {m.to.toFixed(2)}
                      </div>
                      <Badge variant={m.delta > 0 ? 'emerald' : 'amber'}>
                        {m.delta > 0 ? '+' : ''}{m.delta.toFixed(2)}
                      </Badge>
                    </div>
                  ))}
                </GlassCard>
              </Reveal>
            )}
          </>
        )}
      </AsyncState>
    </div>
  )
}
