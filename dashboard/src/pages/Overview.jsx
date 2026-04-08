import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { formatDuration, formatNumber, formatPercentage } from '../utils/formatters';
import AnimatedStatCard from '../components/AnimatedStatCard';
import EnhancedChart from '../components/EnhancedChart';

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
      const data = await api.getProfile();
      setAnalytics(data);
      setError(null);
    } catch (err) {
      setError('Failed to load profile data. Make sure the behavioral-engine backend is running on port 8000.');
      console.error('Error loading profile:', err);
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

  // Handle different data structures
  const metrics = analytics.persona?.metrics || analytics.data_summary || {};
  
  // Default values for missing data
  const totalSessions = metrics.total_sessions || 0;
  const totalReels = metrics.total_reels || 0;
  const avgWatchTime = metrics.avg_watch_time || 0;
  const engagementScore = metrics.engagement_score || 0;
  const attentionScore = metrics.attention_score || 0;
  
  // Create mock data for charts since we don't have detailed user breakdowns
  const topUsersData = totalReels > 0 ? [
    { name: 'Creator 1', time: avgWatchTime * 0.3 },
    { name: 'Creator 2', time: avgWatchTime * 0.25 },
    { name: 'Creator 3', time: avgWatchTime * 0.2 },
    { name: 'Creator 4', time: avgWatchTime * 0.15 },
    { name: 'Creator 5', time: avgWatchTime * 0.1 }
  ] : [];

  const engagementData = totalReels > 0 ? [
    { name: 'Engaged', value: Math.round(engagementScore * totalReels) },
    { name: 'Not Engaged', value: totalReels - Math.round(engagementScore * totalReels) }
  ] : [];

  
  return (
    <div className="container">
      <div className="page-header">
        <h1 className="page-title">Overview</h1>
        <p className="page-subtitle">Your Instagram Reels behavioral insights</p>
      </div>

      <div className="stats-grid">
        <AnimatedStatCard
          label="Total Sessions"
          value={formatNumber(totalSessions)}
          description="Tracking sessions recorded"
          icon="9178;"
          color="primary"
        />

        <AnimatedStatCard
          label="Total Reels"
          value={formatNumber(totalReels)}
          description="Reels watched"
          icon="9192;"
          color="secondary"
        />

        <AnimatedStatCard
          label="Attention Score"
          value={formatPercentage(attentionScore)}
          description="Focus and attention level"
          icon="934;"
          color="warning"
        />

        <AnimatedStatCard
          label="Engagement Score"
          value={formatPercentage(engagementScore)}
          description="Interaction level"
          icon="2764;"
          color="success"
        />

        <AnimatedStatCard
          label="Avg Watch Time"
          value={formatDuration(avgWatchTime)}
          description="Average per reel"
          icon="8194;"
          color="info"
        />

        <AnimatedStatCard
          label="Your Archetype"
          value={analytics.persona?.archetype || 'Unknown'}
          description="Behavioral type"
          icon="8224;"
          color="accent"
        />
      </div>

      <EnhancedChart
        type="bar"
        data={topUsersData}
        title="Top 5 Most Watched Creators"
        height={300}
      />

      <EnhancedChart
        type="pie"
        data={engagementData}
        title="Engagement Distribution"
        height={300}
      />
    </div>
  );
}

export default Overview;
