import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { formatDateTime, formatDuration } from '../utils/formatters';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function SessionDetail() {
  const { sessionId } = useParams();
  const [session, setSession] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadSessionData();
  }, [sessionId]);

  const loadSessionData = async () => {
    try {
      setLoading(true);
      const [sessionData, eventsData] = await Promise.all([
        api.getSession(sessionId),
        api.getSessionEvents(sessionId)
      ]);
      setSession(sessionData);
      setEvents(eventsData);
      setError(null);
    } catch (err) {
      setError('Failed to load session details.');
      console.error('Error loading session:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <div className="loading">Loading session details...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="error">{error}</div>
        <Link to="/sessions" className="btn btn-secondary">← Back to Sessions</Link>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="container">
        <div className="empty-state">
          <div className="empty-state-icon">❌</div>
          <div className="empty-state-title">Session Not Found</div>
        </div>
        <Link to="/sessions" className="btn btn-secondary">← Back to Sessions</Link>
      </div>
    );
  }

  const chartData = events.map((event, index) => ({
    index: index + 1,
    watchTime: event.watch_time,
    scrollSpeed: event.scroll_speed
  }));

  const duration = (new Date(session.end_time) - new Date(session.start_time)) / 1000;
  const likedCount = events.filter(e => e.liked).length;
  const likeRatio = events.length > 0 ? (likedCount / events.length * 100).toFixed(1) : 0;

  return (
    <div className="container">
      <div style={{ marginBottom: '24px' }}>
        <Link to="/sessions" className="btn btn-secondary">← Back to Sessions</Link>
      </div>

      <div className="page-header">
        <h1 className="page-title">Session Details</h1>
        <p className="page-subtitle" style={{ fontFamily: 'monospace', fontSize: '14px' }}>
          {session.session_id}
        </p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Start Time</span>
            <span className="stat-icon">🕐</span>
          </div>
          <div className="stat-value" style={{ fontSize: '20px' }}>
            {formatDateTime(session.start_time)}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Duration</span>
            <span className="stat-icon">⏱️</span>
          </div>
          <div className="stat-value">{formatDuration(duration)}</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Total Reels</span>
            <span className="stat-icon">🎬</span>
          </div>
          <div className="stat-value">{session.total_events}</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Watch Time</span>
            <span className="stat-icon">👁️</span>
          </div>
          <div className="stat-value">{formatDuration(session.total_watch_time)}</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Like Ratio</span>
            <span className="stat-icon">❤️</span>
          </div>
          <div className="stat-value">{likeRatio}%</div>
          <div className="stat-description">{likedCount} of {events.length} reels</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Avg Watch Time</span>
            <span className="stat-icon">📊</span>
          </div>
          <div className="stat-value">
            {formatDuration(events.length > 0 ? session.total_watch_time / events.length : 0)}
          </div>
        </div>
      </div>

      {events.length > 0 && (
        <div className="chart-container">
          <h3 className="chart-title">Watch Time Timeline</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="index" label={{ value: 'Reel #', position: 'insideBottom', offset: -5 }} />
              <YAxis label={{ value: 'Watch Time (s)', angle: -90, position: 'insideLeft' }} />
              <Tooltip formatter={(value) => [value.toFixed(2) + 's', 'Watch Time']} />
              <Line type="monotone" dataKey="watchTime" stroke="#667eea" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="table-container">
        <h3 style={{ padding: '24px 24px 0', margin: 0 }}>Events</h3>
        <table className="table">
          <thead>
            <tr>
              <th>#</th>
              <th>Reel ID</th>
              <th>Username</th>
              <th>Caption</th>
              <th>Watch Time</th>
              <th>Liked</th>
              <th>Replays</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event, index) => (
              <tr key={event.id}>
                <td>{index + 1}</td>
                <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                  {event.reel_id.substring(0, 12)}...
                </td>
                <td>@{event.username}</td>
                <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {event.caption || '-'}
                </td>
                <td>{formatDuration(event.watch_time)}</td>
                <td>
                  {event.liked ? (
                    <span className="badge badge-danger">❤️ Liked</span>
                  ) : (
                    <span className="badge" style={{ background: '#f1f5f9', color: '#64748b' }}>-</span>
                  )}
                </td>
                <td>{event.replay_count}</td>
                <td style={{ fontSize: '12px' }}>{formatDateTime(event.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default SessionDetail;
