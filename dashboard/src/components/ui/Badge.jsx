const variantMap = {
  success: { bg: 'rgba(16,185,129,0.15)', text: '#34d399', border: 'rgba(16,185,129,0.25)' },
  warning: { bg: 'rgba(245,158,11,0.15)', text: '#fbbf24', border: 'rgba(245,158,11,0.25)' },
  danger: { bg: 'rgba(239,68,68,0.15)', text: '#f87171', border: 'rgba(239,68,68,0.25)' },
  info: { bg: 'rgba(99,102,241,0.15)', text: '#818cf8', border: 'rgba(99,102,241,0.25)' },
  neutral: { bg: 'rgba(148,163,184,0.1)', text: '#94a3b8', border: 'rgba(148,163,184,0.15)' },
  indigo: { bg: 'rgba(99,102,241,0.12)', text: '#a5b4fc', border: 'rgba(99,102,241,0.2)' },
  amber: { bg: 'rgba(245,158,11,0.12)', text: '#fde68a', border: 'rgba(245,158,11,0.2)' },
  emerald: { bg: 'rgba(16,185,129,0.12)', text: '#6ee7b7', border: 'rgba(16,185,129,0.2)' },
  pink: { bg: 'rgba(236,72,153,0.12)', text: '#f9a8d4', border: 'rgba(236,72,153,0.2)' },
}

export default function Badge({ children, variant = 'neutral', dot = false, className = '', style = {} }) {
  const v = variantMap[variant] || variantMap.neutral
  return (
    <span
      className={className}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: '5px',
        padding: '3px 10px', borderRadius: '100px',
        fontSize: '11px', fontWeight: 600, letterSpacing: '0.02em',
        background: v.bg, color: v.text, border: `1px solid ${v.border}`,
        ...style,
      }}
    >
      {dot && <span style={{ width: 5, height: 5, borderRadius: '50%', background: v.text, flexShrink: 0 }} />}
      {children}
    </span>
  )
}
