import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';
import PageHeader from '../components/PageHeader';
import './OpportunityQueuePage.css';

interface Opportunity {
  id: string;
  requirement: string;
  score: number;
  band: string;
  intent?: string;
  status?: string;
  primary_category?: string;
  source_name?: string;
  source_published_at?: string;
}

const BAND_COLOR_VARS: Record<string, string> = {
  Hot: '--color-band-hot',
  'High potential': '--color-band-high',
  Review: '--color-band-review',
  Archive: '--color-band-archive',
};

const EMPTY_FILTERS = {
  intent: '',
  status: '',
  band: '',
  minScore: 0,
  datePreset: 'any',
};

export default function OpportunityQueuePage() {
  const [rawOpportunities, setRawOpportunities] = useState<Opportunity[]>([]);
  const [nextUrl, setNextUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const navigate = useNavigate();

  const fetchOpportunities = useCallback(() => {
    setLoading(true);
    const params: Record<string, string> = { ordering: '-score' };
    if (filters.intent) params.intent = filters.intent;
    if (filters.status) params.status = filters.status;
    if (filters.band) params.band = filters.band;

    apiClient
      .get('/opportunities/', { params })
      .then((res) => {
        setRawOpportunities(res.data.results ?? res.data);
        setNextUrl(res.data.next ?? null);
      })
      .catch((err) => console.log('Error fetching opportunities:', err))
      .finally(() => setLoading(false));
  }, [filters.intent, filters.status, filters.band]);

  useEffect(() => {
    fetchOpportunities();
  }, [fetchOpportunities]);

  function loadMore() {
    if (!nextUrl) return;
    setLoadingMore(true);
    apiClient
      .get(nextUrl)
      .then((res) => {
        setRawOpportunities((prev) => [...prev, ...(res.data.results ?? [])]);
        setNextUrl(res.data.next ?? null);
      })
      .catch((err) => console.log('Error loading more:', err))
      .finally(() => setLoadingMore(false));
  }

  const displayed = rawOpportunities.filter((o) => {
    if (filters.minScore > 0 && o.score < filters.minScore) return false;
    if (filters.datePreset !== 'any') {
      const days = filters.datePreset === '24h' ? 1 : filters.datePreset === '7d' ? 7 : 30;
      const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
      const published = o.source_published_at ? new Date(o.source_published_at).getTime() : 0;
      if (published < cutoff) return false;
    }
    return true;
  });

  return (
    <div className="queue-page">
      <PageHeader title="Opportunity Queue" />
      <div className="queue-content">
        <div className="queue-filters">
          <div className="queue-filter-field">
            <label>Intent</label>
            <select value={filters.intent} onChange={(e) => setFilters({ ...filters, intent: e.target.value })}>
              <option value="">All</option>
              <option value="buyer">Buyer</option>
              <option value="hiring">Hiring</option>
              <option value="nonbuyer">Non-buyer</option>
              <option value="uncertain">Uncertain</option>
            </select>
          </div>
          <div className="queue-filter-field">
            <label>Status</label>
            <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
              <option value="">All</option>
              <option value="new">New</option>
              <option value="review">Review</option>
              <option value="contacted">Contacted</option>
              <option value="closed">Closed</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
          <div className="queue-filter-field">
            <label>Score band</label>
            <select value={filters.band} onChange={(e) => setFilters({ ...filters, band: e.target.value })}>
              <option value="">All</option>
              <option value="Hot">Hot</option>
              <option value="High potential">High potential</option>
              <option value="Review">Review</option>
              <option value="Archive">Archive</option>
            </select>
          </div>
          <div className="queue-filter-field">
            <label>Min score</label>
            <input
              type="number"
              min={0}
              max={100}
              value={filters.minScore}
              onChange={(e) => setFilters({ ...filters, minScore: parseInt(e.target.value, 10) || 0 })}
            />
          </div>
          <div className="queue-filter-field">
            <label>Detected within</label>
            <select value={filters.datePreset} onChange={(e) => setFilters({ ...filters, datePreset: e.target.value })}>
              <option value="any">Any time</option>
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
            </select>
          </div>
          <button className="queue-clear-button" onClick={() => setFilters(EMPTY_FILTERS)}>
            Clear all
          </button>
        </div>

        {loading ? (
          <div className="queue-loading">Loading...</div>
        ) : displayed.length === 0 ? (
          <p className="queue-empty">No opportunities match these filters.</p>
        ) : (
          <>
            {displayed.map((item) => (
              <div key={item.id} className="queue-card" onClick={() => navigate(`/lead/${item.id}`)}>
                <p className="queue-card-title">{item.requirement ?? 'Untitled'}</p>
                <div className="queue-card-meta-row">
                  <span
                    className="queue-card-band"
                    style={{ color: `var(${BAND_COLOR_VARS[item.band] ?? '--color-text-muted'})` }}
                  >
                    {item.band}
                  </span>
                  <span className="queue-card-score">Score: {item.score}</span>
                </div>
              </div>
            ))}
            {nextUrl && (
              <button className="queue-load-more" onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? 'Loading...' : 'Load more'}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}