import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { formatDuration, formatNumber, formatPercentage } from '../utils/formatters';

function Analytics() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      const data = await api.getAnalytics();
      setAnalytics(data);
      setError(null);
    } catch (err) {
      setError('Failed to load analytics.');
      console.error('Error loading analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <div className="loading">Loading analytics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="error">{error}</div>
      </div>
    );
  }

  if (!analytics || analytics.total_events === 0) {
    return (
      <div className="container">
        <div className="page-header">
          <h1 className="page-title">Analytics</h1>
          <p className="page-subtitle">Detailed behavioral insights</p>
        </div>
        <div className="empty-state">
          <div className="empty-state-icon">📈</div>
          <div className="empty-state-title">No Data Yet</div>
          <div className="empty-state-description">
            Start tracking your Instagram Reels behavior to see analytics
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="page-header">
        <h1 className="page-title">Analytics</h1>
        <p className="page-subtitle">Comprehensive behavioral insights</p>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ marginBottom: '16px' }}>📊 Overall Statistics</h3>
        <div className="stats-grid">
          <div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Total Sessions
            </div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--primary)' }}>
              {formatNumber(analytics.total_sessions)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Total Reels Watched
            </div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--primary)' }}>
              {formatNumber(analytics.total_events)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Total Watch Time
            </div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--primary)' }}>
              {formatDuration(analytics.total_watch_time)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Total Replays
            </div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--primary)' }}>
              {formatNumber(analytics.total_replays)}
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ marginBottom: '16px' }}>⏱️ Time Metrics</h3>
        <div className="stats-grid">
          <div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Avg Watch Time per Reel
            </div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--primary)' }}>
              {formatDuration(analytics.avg_watch_time_per_reel)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Avg Watch Time per Session
            </div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--primary)' }}>
              {formatDuration(analytics.avg_watch_time_per_session)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Reels per Session
            </div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--primary)' }}>
              {analytics.reels_per_session.toFixed(1)}
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ marginBottom: '16px' }}>💝 Engagement Metrics</h3>
        <div className="stats-grid">
          <div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Like Ratio
            </div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--primary)' }}>
              {formatPercentage(analytics.like_ratio)}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              {Math.round((analytics.like_ratio / 100) * analytics.total_events)} of {analytics.total_events} reels
            </div>
          </div>
          <div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Avg Scroll Speed
            </div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--primary)' }}>
              {analytics.avg_scroll_speed.toFixed(1)} px/s
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: '16px' }}>👥 Most Watched Creators</h3>
        {analytics.most_watched_users.length > 0 ? (
          <div className="table-container" style={{ boxShadow: 'none', border: 'none' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Username</th>
                  <th>Views</th>
                  <th>Total Watch Time</th>
                  <th>Avg Watch Time</th>
                </tr>
              </thead>
              <tbody>
                {analytics.most_watched_users.map((user, index) => (
                  <tr key={index}>
                    <td>
                      <span style={{ fontSize: '20px' }}>
                        {index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `#${index + 1}`}
                      </span>
                    </td>
                    <td>
                      <strong>@{user.username}</strong>
                    </td>
                    <td>
                      <span className="badge badge-success">{user.view_count}</span>
                    </td>
                    <td>{formatDuration(user.total_watch_time)}</td>
                    <td>{formatDuration(user.total_watch_time / user.view_count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <p>No creator data available yet</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Analytics;
