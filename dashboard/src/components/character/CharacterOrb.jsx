import { useEffect, useRef } from 'react'

/**
 * CharacterOrb — a living visualization of the character's real cognitive
 * state, not a decorative animation. Every visual property maps to real data:
 *
 *   confidence   -> core brightness/solidity (dim & wispy when uncertain,
 *                   bright & stable when confident)
 *   topics       -> orbiting particles, one per dominant topic, colored by
 *                   index and labeled on hover via the legend below the orb
 *   inferenceCount -> particle count floor (more active reasoning = more
 *                   motes in the field even without many topics)
 *   moodColor    -> aura tint (e.g. from wellbeing risk or RL Q-value) —
 *                   emerald/amber/rose, defaults to the app's indigo/violet
 *   thinking     -> true while a query is in flight: pulse rate and particle
 *                   orbit speed both increase, particles pull inward, a
 *                   "thinking ring" sweeps around the core
 *
 * Pure Canvas 2D + requestAnimationFrame — no new dependencies.
 */
export default function CharacterOrb({
  confidence = 0.5,
  topics = [],
  inferenceCount = 0,
  moodColor = null,
  thinking = false,
  size = 160,
}) {
  const canvasRef = useRef(null)
  const rafRef = useRef(null)
  const stateRef = useRef({ t: 0, particles: [] })

  // Rebuild the particle set when topic/inference count changes (not every frame).
  useEffect(() => {
    const count = Math.max(topics.length, Math.min(inferenceCount, 8), 3)
    const particles = Array.from({ length: count }, (_, i) => ({
      angle: (i / count) * Math.PI * 2,
      radiusJitter: 0.85 + (i % 3) * 0.08,
      speed: 0.35 + (i % 4) * 0.12,
      label: topics[i] || null,
      hue: (i * 47) % 360,
    }))
    stateRef.current.particles = particles
  }, [topics.join('|'), inferenceCount])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    canvas.width = size * dpr
    canvas.height = size * dpr
    ctx.scale(dpr, dpr)

    const cx = size / 2, cy = size / 2
    const coreR = size * 0.22

    // Base palette from the app's design system; mood tint overrides when given.
    const baseA = moodColor || '#6366f1'
    const baseB = moodColor ? moodColor : '#a855f7'

    function draw(ts) {
      const st = stateRef.current
      const dt = 0.016
      st.t += dt * (thinking ? 2.2 : 1)

      ctx.clearRect(0, 0, size, size)

      // Breathing pulse: slow idle, faster + tighter while "thinking".
      const pulseSpeed = thinking ? 3.2 : 1.0
      const pulse = 0.5 + 0.5 * Math.sin(st.t * pulseSpeed)
      const brightness = 0.35 + confidence * 0.65
      const coreRadius = coreR * (0.92 + pulse * 0.1 * (thinking ? 1.6 : 1))

      // Outer aura (soft glow) — size/opacity driven by confidence.
      const auraR = coreRadius * (2.2 + pulse * 0.3)
      const aura = ctx.createRadialGradient(cx, cy, coreRadius * 0.3, cx, cy, auraR)
      aura.addColorStop(0, hexAlpha(baseA, 0.35 * brightness))
      aura.addColorStop(0.6, hexAlpha(baseB, 0.12 * brightness))
      aura.addColorStop(1, hexAlpha(baseB, 0))
      ctx.fillStyle = aura
      ctx.beginPath()
      ctx.arc(cx, cy, auraR, 0, Math.PI * 2)
      ctx.fill()

      // Thinking ring: a sweeping arc while a query is in flight.
      if (thinking) {
        ctx.save()
        ctx.strokeStyle = hexAlpha('#ffffff', 0.5)
        ctx.lineWidth = 2
        ctx.beginPath()
        const sweep = (st.t * 3) % (Math.PI * 2)
        ctx.arc(cx, cy, coreRadius * 1.55, sweep, sweep + Math.PI * 0.6)
        ctx.stroke()
        ctx.restore()
      }

      // Core orb.
      const core = ctx.createRadialGradient(
        cx - coreRadius * 0.3, cy - coreRadius * 0.3, coreRadius * 0.1,
        cx, cy, coreRadius
      )
      core.addColorStop(0, hexAlpha('#ffffff', 0.9 * brightness))
      core.addColorStop(0.35, hexAlpha(baseA, brightness))
      core.addColorStop(1, hexAlpha(baseB, 0.85 * brightness))
      ctx.fillStyle = core
      ctx.beginPath()
      ctx.arc(cx, cy, coreRadius, 0, Math.PI * 2)
      ctx.fill()

      // Orbiting particles — one per topic/inference, drifting continuously.
      const orbitSpeedMul = thinking ? 2.4 : 1
      const orbitR = coreRadius * (thinking ? 1.5 : 1.9)
      for (const p of st.particles) {
        const a = p.angle + st.t * p.speed * orbitSpeedMul
        const r = orbitR * p.radiusJitter
        const px = cx + Math.cos(a) * r
        const py = cy + Math.sin(a) * r * 0.82 // slight ellipse for depth
        const pr = 2.4 + Math.sin(st.t * 2 + p.angle) * 0.8

        ctx.beginPath()
        ctx.fillStyle = hexAlpha(baseA, 0.85)
        ctx.shadowColor = baseA
        ctx.shadowBlur = 6
        ctx.arc(px, py, pr, 0, Math.PI * 2)
        ctx.fill()
        ctx.shadowBlur = 0
      }

      rafRef.current = requestAnimationFrame(draw)
    }

    rafRef.current = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(rafRef.current)
  }, [confidence, moodColor, thinking, size])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      <canvas ref={canvasRef} style={{ width: size, height: size, display: 'block' }} />
    </div>
  )
}

function hexAlpha(hex, alpha) {
  const h = hex.replace('#', '')
  const r = parseInt(h.substring(0, 2), 16)
  const g = parseInt(h.substring(2, 4), 16)
  const b = parseInt(h.substring(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}
