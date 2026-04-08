import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { formatDateTime, formatDuration, formatRelativeTime } from '../utils/formatters';

function Sessions() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await api.getSessions();
      setSessions(data);
      setError(null);
    } catch (err) {
      setError('Failed to load sessions. Make sure the backend is running.');
      console.error('Error loading sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (sessionId) => {
    if (!confirm('Are you sure you want to delete this session?')) {
      return;
    }

    try {
      await api.deleteSession(sessionId);
      setSessions(sessions.filter(s => s.session_id !== sessionId));
    } catch (err) {
      alert('Failed to delete session');
      console.error('Error deleting session:', err);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <div className="loading">Loading sessions...</div>
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

  if (sessions.length === 0) {
    return (
      <div className="container">
        <div className="page-header">
          <h1 className="page-title">Sessions</h1>
          <p className="page-subtitle">View all your tracking sessions</p>
        </div>
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <div className="empty-state-title">No Sessions Yet</div>
          <div className="empty-state-description">
            Start using the Chrome extension to create tracking sessions
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="page-header">
        <h1 className="page-title">Sessions</h1>
        <p className="page-subtitle">{sessions.length} tracking sessions recorded</p>
      </div>

      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Session ID</th>
              <th>Start Time</th>
              <th>Duration</th>
              <th>Events</th>
              <th>Watch Time</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((session) => {
              const duration = (new Date(session.end_time) - new Date(session.start_time)) / 1000;
              return (
                <tr key={session.id}>
                  <td>
                    <Link to={`/sessions/${session.session_id}`} style={{ fontFamily: 'monospace', fontSize: '13px' }}>
                      {session.session_id.substring(0, 20)}...
                    </Link>
                  </td>
                  <td>
                    <div>{formatDateTime(session.start_time)}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {formatRelativeTime(session.start_time)}
                    </div>
                  </td>
                  <td>{formatDuration(duration)}</td>
                  <td>
                    <span className="badge badge-success">{session.total_events}</span>
                  </td>
                  <td>{formatDuration(session.total_watch_time)}</td>
                  <td>
                    <button 
                      onClick={() => handleDelete(session.session_id)}
                      className="btn btn-secondary"
                      style={{ padding: '6px 12px', fontSize: '13px' }}
                    >
                      🗑️ Delete
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Sessions;
