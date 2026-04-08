import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { formatDuration, formatNumber, formatPercentage } from '../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

function Overview() {
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
      setError('Failed to load analytics. Make sure the backend is running.');
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

  if (!analytics) {
    return (
      <div className="container">
        <div className="empty-state">
          <div className="empty-state-icon">📊</div>
          <div className="empty-state-title">No Data Yet</div>
          <div className="empty-state-description">
            Start using the Chrome extension to track your Instagram Reels behavior
          </div>
        </div>
      </div>
    );
  }

  const topUsersData = analytics.most_watched_users.slice(0, 5).map(user => ({
    name: user.username,
    time: parseFloat(user.total_watch_time.toFixed(1))
  }));

  const engagementData = [
    { name: 'Liked', value: Math.round((analytics.like_ratio / 100) * analytics.total_events) },
    { name: 'Not Liked', value: analytics.total_events - Math.round((analytics.like_ratio / 100) * analytics.total_events) }
  ];

  const COLORS = ['#667eea', '#e2e8f0'];

  return (
    <div className="container">
      <div className="page-header">
        <h1 className="page-title">Overview</h1>
        <p className="page-subtitle">Your Instagram Reels behavioral insights</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Total Sessions</span>
            <span className="stat-icon">📅</span>
          </div>
          <div className="stat-value">{formatNumber(analytics.total_sessions)}</div>
          <div className="stat-description">Tracking sessions recorded</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Total Reels</span>
            <span className="stat-icon">🎬</span>
          </div>
          <div className="stat-value">{formatNumber(analytics.total_events)}</div>
          <div className="stat-description">Reels watched</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Watch Time</span>
            <span className="stat-icon">⏱️</span>
          </div>
          <div className="stat-value">{formatDuration(analytics.total_watch_time)}</div>
          <div className="stat-description">Total time spent</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Like Ratio</span>
            <span className="stat-icon">❤️</span>
          </div>
          <div className="stat-value">{formatPercentage(analytics.like_ratio)}</div>
          <div className="stat-description">Reels you liked</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Avg per Reel</span>
            <span className="stat-icon">📊</span>
          </div>
          <div className="stat-value">{formatDuration(analytics.avg_watch_time_per_reel)}</div>
          <div className="stat-description">Average watch time</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Reels/Session</span>
            <span className="stat-icon">🔢</span>
          </div>
          <div className="stat-value">{analytics.reels_per_session.toFixed(1)}</div>
          <div className="stat-description">Average per session</div>
        </div>
      </div>

      <div className="chart-container">
        <h3 className="chart-title">Top 5 Most Watched Creators</h3>
        {topUsersData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={topUsersData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip 
                formatter={(value) => [formatDuration(value), 'Watch Time']}
              />
              <Bar dataKey="time" fill="#667eea" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty-state">
            <p>No data available yet</p>
          </div>
        )}
      </div>

      <div className="chart-container">
        <h3 className="chart-title">Engagement Distribution</h3>
        {analytics.total_events > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={engagementData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {engagementData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty-state">
            <p>No data available yet</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Overview;
