function SkeletonCard() {
  return (
    <div className="stat-card" style={{ pointerEvents: 'none' }}>
      <div className="stat-header">
        <div className="skeleton skeleton-text" style={{ width: '100px', height: '14px' }} />
        <div className="skeleton skeleton-circle" style={{ width: '24px', height: '24px' }} />
      </div>
      <div className="skeleton skeleton-text" style={{ width: '160px', height: '36px', marginBottom: '4px' }} />
      <div className="skeleton skeleton-text" style={{ width: '80px', height: '12px' }} />
    </div>
  );
}

function SkeletonTable({ rows = 5 }) {
  return (
    <div className="table-container">
      <div style={{ padding: '16px' }}>
        <div className="skeleton skeleton-text" style={{ width: '200px', height: '14px', marginBottom: '16px' }} />
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} style={{ display: 'flex', gap: '16px', padding: '12px 0', borderTop: i > 0 ? '1px solid var(--border)' : 'none' }}>
            <div className="skeleton skeleton-text" style={{ width: '20%', height: '14px' }} />
            <div className="skeleton skeleton-text" style={{ width: '25%', height: '14px' }} />
            <div className="skeleton skeleton-text" style={{ width: '15%', height: '14px' }} />
            <div className="skeleton skeleton-text" style={{ width: '10%', height: '14px' }} />
            <div className="skeleton skeleton-text" style={{ width: '15%', height: '14px' }} />
          </div>
        ))}
      </div>
    </div>
  );
}

function SkeletonChart({ height = 300 }) {
  return (
    <div className="chart-container">
      <div className="skeleton skeleton-text" style={{ width: '250px', height: '18px', marginBottom: '20px' }} />
      <div className="skeleton" style={{ width: '100%', height: `${height - 80}px`, borderRadius: '8px' }} />
    </div>
  );
}

export function LoadingSkeleton({ type = 'cards', count = 6, rows = 5, height }) {
  if (type === 'cards') {
    return (
      <div className="container">
        <div className="page-header">
          <div className="skeleton skeleton-text" style={{ width: '200px', height: '32px', marginBottom: '8px' }} />
          <div className="skeleton skeleton-text" style={{ width: '300px', height: '16px' }} />
        </div>
        <div className="stats-grid">
          {Array.from({ length: count }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (type === 'table') {
    return (
      <div className="container">
        <div className="page-header">
          <div className="skeleton skeleton-text" style={{ width: '200px', height: '32px', marginBottom: '8px' }} />
          <div className="skeleton skeleton-text" style={{ width: '300px', height: '16px' }} />
        </div>
        <SkeletonTable rows={rows} />
      </div>
    );
  }

  if (type === 'chart') {
    return (
      <div className="container">
        <div className="page-header">
          <div className="skeleton skeleton-text" style={{ width: '200px', height: '32px', marginBottom: '8px' }} />
          <div className="skeleton skeleton-text" style={{ width: '300px', height: '16px' }} />
        </div>
        <SkeletonChart height={height} />
      </div>
    );
  }

  if (type === 'detail') {
    return (
      <div className="container">
        <div className="skeleton skeleton-text" style={{ width: '100px', height: '14px', marginBottom: '24px' }} />
        <div className="page-header">
          <div className="skeleton skeleton-text" style={{ width: '250px', height: '32px', marginBottom: '8px' }} />
          <div className="skeleton skeleton-text" style={{ width: '300px', height: '16px' }} />
        </div>
        <div className="stats-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <SkeletonChart height={300} />
        <SkeletonTable rows={5} />
      </div>
    );
  }

  return null;
}

export default LoadingSkeleton;