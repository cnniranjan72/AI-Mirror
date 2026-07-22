export default function LoadingSkeleton({ type = 'card', count = 1, rows = 4, height }) {
  if (type === 'card') {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '16px' }}>
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="card" style={{ padding: '24px', animationDelay: `${i * 80}ms` }}>
            <div className="skeleton" style={{ width: '40%', height: 12, marginBottom: 16, borderRadius: 4 }} />
            <div className="skeleton" style={{ width: '70%', height: 28, marginBottom: 8, borderRadius: 6 }} />
            <div className="skeleton" style={{ width: '50%', height: 12, borderRadius: 4 }} />
          </div>
        ))}
      </div>
    )
  }
  if (type === 'chart') {
    return (
      <div className="card" style={{ padding: '24px' }}>
        <div className="skeleton" style={{ width: '30%', height: 16, marginBottom: 24, borderRadius: 4 }} />
        <div className="skeleton" style={{ width: '100%', height: height || 250, borderRadius: 8 }} />
      </div>
    )
  }
  if (type === 'table') {
    return (
      <div className="card" style={{ padding: '24px' }}>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} style={{ display: 'flex', gap: 16, marginBottom: 12, alignItems: 'center' }}>
            <div className="skeleton" style={{ width: '25%', height: 14, borderRadius: 4 }} />
            <div className="skeleton" style={{ width: '35%', height: 14, borderRadius: 4 }} />
            <div className="skeleton" style={{ width: '20%', height: 14, borderRadius: 4 }} />
            <div className="skeleton" style={{ width: '20%', height: 14, borderRadius: 4 }} />
          </div>
        ))}
      </div>
    )
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton" style={{ width: '100%', height: height || 48, borderRadius: 8 }} />
      ))}
    </div>
  )
}
