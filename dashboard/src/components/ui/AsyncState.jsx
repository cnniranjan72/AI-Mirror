import LoadingSkeleton from './LoadingSkeleton'

/**
 * Shared loading/error/empty wrapper for pages built on useApi()'s
 * {data, loading, error} shape. Built from existing-but-underused primitives
 * (.empty-state* CSS, LoadingSkeleton) rather than new styling — those
 * classes previously were only consumed by ErrorBoundary.jsx.
 *
 * Exists because several pages (Behavior/Memory/Analytics, confirmed) read
 * `error` off useApi() and never rendered it, so a broken fetch looked
 * identical to "no data yet" — this makes the three states visually
 * distinct everywhere it's used.
 */
export default function AsyncState({
  loading,
  error,
  empty,
  onRetry,
  loadingFallback = <LoadingSkeleton type="card" count={3} />,
  emptyIcon = '📭',
  emptyTitle = 'Nothing here yet',
  emptyDescription,
  children,
}) {
  if (loading) return loadingFallback

  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠️</div>
        <div className="empty-state-title">Couldn't load this</div>
        <div className="empty-state-description">
          {typeof error === 'string' ? error : 'Something went wrong talking to the backend.'}
        </div>
        {onRetry && (
          <button className="btn btn-secondary" onClick={onRetry} style={{ marginTop: 16 }}>
            Try again
          </button>
        )}
      </div>
    )
  }

  if (empty) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">{emptyIcon}</div>
        <div className="empty-state-title">{emptyTitle}</div>
        {emptyDescription && <div className="empty-state-description">{emptyDescription}</div>}
      </div>
    )
  }

  return children
}
