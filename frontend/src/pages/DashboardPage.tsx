import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';
import { formatPosted } from '../utils/posted';
import './DashboardPage.css';

interface Opportunity {
  id: string;
  requirement: string;
  score: number;
  band: string;
  detected_at?: string;
  source_published_at?: string;
}

interface DashboardStats {
  collected: number;
  hot: number;
  review: number;
  contacted: number;
}

interface PostedCounts {
  today: number;
  week: number;
  month: number;
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [stats, setStats] = useState<DashboardStats>({ collected: 0, hot: 0, review: 0, contacted: 0 });
  const [posted, setPosted] = useState<PostedCounts>({ today: 0, week: 0, month: 0 });
  const [latest, setLatest] = useState<Opportunity[]>([]);
  const navigate = useNavigate();

  const loadDashboard = useCallback(async () => {
    setLoadError(false);
    try {
      const [baseline, summary, hot, review, contacted] = await Promise.all([
        apiClient.get('/opportunities/', { params: { ordering: '-detected_at' } }),
        apiClient.get('/opportunities/stats/'),
        apiClient.get('/opportunities/', { params: { band: 'Hot' } }),
        apiClient.get('/opportunities/', { params: { status: 'review' } }),
        apiClient.get('/opportunities/', { params: { status: 'contacted' } }),
      ]);

      const results: Opportunity[] = baseline.data.results ?? baseline.data;

      setPosted({
        today: summary.data.posted?.today ?? 0,
        week: summary.data.posted?.week ?? 0,
        month: summary.data.posted?.month ?? 0,
      });
      setStats({
        collected: summary.data.collected ?? 0,
        hot: hot.data.count ?? 0,
        review: review.data.count ?? 0,
        contacted: contacted.data.count ?? 0,
      });

      // "Latest Opportunities" should only show genuinely relevant leads —
      // Archive-band items are low-score/rejected (junk, seller promotion, etc.)
      // and would otherwise confuse anyone viewing the dashboard.
      const relevantResults = results.filter((o) => o.band !== 'Archive');
      setLatest(relevantResults.slice(0, 3));
    } catch (err) {
      console.log('Error loading dashboard:', err);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  if (loading) {
    return <div className="dashboard-loading">Loading...</div>;
  }

  return (
    <div className="dashboard-page">
      <h1 className="dashboard-welcome">Welcome back</h1>

      {loadError && (
        <p className="dashboard-error" role="alert">
          Couldn't load the latest figures.{' '}
          <button className="dashboard-retry" onClick={loadDashboard}>
            Try again
          </button>
        </p>
      )}

      <div className="dashboard-stats-grid">
        <StatTile
          label="Total Collected"
          value={stats.collected}
          colorVar="--color-primary"
          onClick={() => navigate('/opportunities')}
        />
        <StatTile label="Hot Opportunities" value={stats.hot} colorVar="--color-hot" />
        <StatTile
          label="Under Review"
          value={stats.review}
          colorVar="--color-text-muted"
          onClick={() => navigate('/review')}
        />
        <StatTile label="Contacted" value={stats.contacted} colorVar="--color-info" />
      </div>

      <h2 className="dashboard-section-title">Freshness of leads</h2>
      <div className="dashboard-stats-grid dashboard-freshness-grid">
        <StatTile
          label="Posted today"
          value={posted.today}
          colorVar="--color-primary"
          onClick={() => navigate('/opportunities?posted=today')}
        />
        <StatTile
          label="Last 7 days"
          value={posted.week}
          colorVar="--color-info"
          onClick={() => navigate('/opportunities?posted=week')}
        />
        <StatTile
          label="Last 30 days"
          value={posted.month}
          colorVar="--color-text-muted"
          onClick={() => navigate('/opportunities?posted=month')}
        />
      </div>

            <button className="dashboard-primary-button" onClick={() => navigate('/opportunities')}>
        View All Opportunities →
      </button>

            <h2 className="dashboard-section-title">Latest Opportunities</h2>
      {latest.length === 0 && <p className="dashboard-empty">No opportunities yet.</p>}
      <div className="dashboard-latest-grid">
        {latest.map((item) => (
          <div key={item.id} className="dashboard-latest-card" onClick={() => navigate(`/lead/${item.id}`)}>
            <p className="dashboard-latest-title">{item.requirement ?? 'Untitled'}</p>
            <p className="dashboard-latest-meta">
              {item.band} · Score {item.score}
              {formatPosted(item.source_published_at ?? item.detected_at) &&
                ` · Posted ${formatPosted(item.source_published_at ?? item.detected_at).toLowerCase()}`}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatTile({
  label,
  value,
  colorVar,
  onClick,
}: {
  label: string;
  value: number;
  colorVar: string;
  onClick?: () => void;
}) {
  return (
    <div className={`dashboard-stat-tile${onClick ? ' clickable' : ''}`} onClick={onClick}>
      <p className="dashboard-stat-value" style={{ color: `var(${colorVar})` }}>
        {value}
      </p>
      <p className="dashboard-stat-label">{label}</p>
    </div>
  );
}