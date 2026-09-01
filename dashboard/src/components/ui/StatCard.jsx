import Tilt from '../motion/Tilt'
import CountUp from '../motion/CountUp'

const accentMap = {
  indigo: { bg: 'rgba(99,102,241,0.1)', border: 'rgba(99,102,241,0.2)', text: '#818cf8', glow: 'rgba(99,102,241,0.55)', gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)' },
  violet: { bg: 'rgba(139,92,246,0.1)', border: 'rgba(139,92,246,0.2)', text: '#a78bfa', glow: 'rgba(139,92,246,0.55)', gradient: 'linear-gradient(135deg, #8b5cf6, #7c3aed)' },
  pink: { bg: 'rgba(236,72,153,0.1)', border: 'rgba(236,72,153,0.2)', text: '#f472b6', glow: 'rgba(236,72,153,0.55)', gradient: 'linear-gradient(135deg, #ec4899, #db2777)' },
  emerald: { bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.2)', text: '#34d399', glow: 'rgba(16,185,129,0.55)', gradient: 'linear-gradient(135deg, #10b981, #059669)' },
  amber: { bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.2)', text: '#fbbf24', glow: 'rgba(245,158,11,0.55)', gradient: 'linear-gradient(135deg, #f59e0b, #d97706)' },
  rose: { bg: 'rgba(244,63,94,0.1)', border: 'rgba(244,63,94,0.2)', text: '#fb7185', glow: 'rgba(244,63,94,0.55)', gradient: 'linear-gradient(135deg, #f43f5e, #e11d48)' },
  cyan: { bg: 'rgba(6,182,212,0.1)', border: 'rgba(6,182,212,0.2)', text: '#22d3ee', glow: 'rgba(6,182,212,0.55)', gradient: 'linear-gradient(135deg, #06b6d4, #0891b2)' },
}

/**
 * The app's primary metric tile. Props are unchanged from the original — every
 * existing call site across the dashboard keeps working untouched — while the
 * presentation gains 3D tilt, a cursor spotlight, an accent underglow, and a
 * counting value.
 *
 * The count-up is safe on every value these pages pass because CountUp only
 * animates a value it can parse a number out of; "--", "v33", "62%" and plain
 * integers all render correctly (see parseAnimatableValue).
 */
export default function StatCard({ label, value, subtitle, icon: Icon, accent = 'indigo', trend, trendLabel, onClick, loading = false }) {
  const colors = accentMap[accent] || accentMap.indigo

  if (loading) {
    return (
      <div className="card" style={{ padding: '24px' }}>
        <div className="skeleton" style={{ width: '80px', height: '14px', marginBottom: '12px', borderRadius: '4px' }} />
        <div className="skeleton" style={{ width: '120px', height: '32px', marginBottom: '8px', borderRadius: '6px' }} />
        <div className="skeleton" style={{ width: '100px', height: '12px', borderRadius: '4px' }} />
      </div>
    )
  }

  return (
    <Tilt max={7} scale={1.02} style={{ height: '100%' }} innerStyle={{ height: '100%' }}>
      <div
        className="card card-gradient spotlight"
        style={{
          padding: '24px', height: '100%',
          cursor: onClick ? 'pointer' : 'default',
          position: 'relative', overflow: 'hidden',
          borderRadius: 'var(--radius-xl)',
        }}
        onClick={onClick}
        role={onClick ? 'button' : undefined}
        tabIndex={onClick ? 0 : undefined}
        // Click-to-navigate tiles were mouse-only before; the same action is
        // now reachable from the keyboard.
        onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(e) } } : undefined}
      >
        {/* Accent wash in the corner — reads as the tile being lit by its own
            metric colour rather than having a coloured badge stuck on it. */}
        <div style={{
          position: 'absolute', top: -40, right: -40, width: 140, height: 140,
          borderRadius: '50%', pointerEvents: 'none',
          background: `radial-gradient(circle, ${colors.glow}, transparent 68%)`,
          opacity: 0.14, filter: 'blur(6px)',
        }} />

        <div className="tilt-layer" style={{ '--z': '26px', position: 'relative' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-tertiary)' }}>
              {label}
            </span>
            {Icon && (
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: colors.bg, border: `1px solid ${colors.border}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: colors.text,
                boxShadow: `0 0 18px -6px ${colors.glow}`,
              }}>
                <Icon />
              </div>
            )}
          </div>

          <div style={{
            fontSize: '30px', fontWeight: 700, lineHeight: 1.1, marginBottom: '6px',
            background: colors.gradient,
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
          }}>
            <CountUp value={value} />
          </div>

          {subtitle && <div style={{ fontSize: '13px', color: 'var(--text-tertiary)', lineHeight: 1.4 }}>{subtitle}</div>}

          {trend !== undefined && (
            <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: trend >= 0 ? 'var(--emerald-400)' : 'var(--rose-400)' }}>
                {trend >= 0 ? '+' : ''}{trend}%
              </span>
              {trendLabel && <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{trendLabel}</span>}
            </div>
          )}
        </div>

        {/* Bottom accent rail. Draws itself in on mount, so a grid of tiles
            resolves as a sequence instead of appearing all at once. */}
        <div className="grow-w" style={{
          position: 'absolute', left: 0, bottom: 0, height: 2, width: '100%',
          background: colors.gradient, opacity: 0.55,
        }} />
      </div>
    </Tilt>
  )
}
