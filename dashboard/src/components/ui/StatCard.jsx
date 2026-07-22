

const accentMap = {
  indigo: { bg: 'rgba(99,102,241,0.1)', border: 'rgba(99,102,241,0.2)', text: '#818cf8', gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)' },
  violet: { bg: 'rgba(139,92,246,0.1)', border: 'rgba(139,92,246,0.2)', text: '#a78bfa', gradient: 'linear-gradient(135deg, #8b5cf6, #7c3aed)' },
  pink: { bg: 'rgba(236,72,153,0.1)', border: 'rgba(236,72,153,0.2)', text: '#f472b6', gradient: 'linear-gradient(135deg, #ec4899, #db2777)' },
  emerald: { bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.2)', text: '#34d399', gradient: 'linear-gradient(135deg, #10b981, #059669)' },
  amber: { bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.2)', text: '#fbbf24', gradient: 'linear-gradient(135deg, #f59e0b, #d97706)' },
  rose: { bg: 'rgba(244,63,94,0.1)', border: 'rgba(244,63,94,0.2)', text: '#fb7185', gradient: 'linear-gradient(135deg, #f43f5e, #e11d48)' },
  cyan: { bg: 'rgba(6,182,212,0.1)', border: 'rgba(6,182,212,0.2)', text: '#22d3ee', gradient: 'linear-gradient(135deg, #06b6d4, #0891b2)' },
}

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
    <div
      className="card card-gradient"
      style={{
        padding: '24px', cursor: onClick ? 'pointer' : 'default', position: 'relative', overflow: 'hidden',
        transition: 'all 0.3s cubic-bezier(0.16,1,0.3,1)',
      }}
      onClick={onClick}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
        <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-tertiary)' }}>
          {label}
        </span>
        {Icon && (
          <div style={{ width: 36, height: 36, borderRadius: 10, background: colors.bg, border: `1px solid ${colors.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: colors.text }}>
            <Icon />
          </div>
        )}
      </div>
      <div style={{ fontSize: '28px', fontWeight: 700, lineHeight: 1.1, marginBottom: '6px', background: colors.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
        {value}
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
  )
}
