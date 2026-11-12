import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import apiClient from '../api/apiClient';
import PageHeader from '../components/PageHeader';
import { POSTED_OPTIONS, formatPosted, isPostedWindow } from '../utils/posted';
import './OpportunityQueuePage.css';

interface Opportunity {
  id: string;
  requirement: string;
  score: number;
  band: string;
  intent?: string;
  kind?: string;
  status?: string;
  primary_category?: string;
  source_name?: string;
  source_published_at?: string;
  detected_at?: string;
}

const KIND_LABELS: Record<string, string> = {
  direct_purchase: 'Direct project request',
  rfp: 'RFP / tender',
  agency_staffing: 'Agency / staffing request',
  hiring_signal: 'Hiring signal (employment)',
  indirect_pain: 'Indirect pain point',
  seller_promotion: 'Seller promotion (agency content)',
  other: 'Other',
};

const BAND_COLOR_VARS: Record<string, string> = {
  Hot: '--color-band-hot',
  'High potential': '--color-band-high',
  Review: '--color-band-review',
  Archive: '--color-band-archive',
};

const EMPTY_FILTERS = {
  intent: '',
  kind: '',
  status: '',
  band: '',
  minScore: 0,
  posted: '',
};

export default function OpportunityQueuePage() {
  const [rawOpportunities, setRawOpportunities] = useState<Opportunity[]>([]);
  const [nextUrl, setNextUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [searchParams] = useSearchParams();
  const initialPosted = searchParams.get('posted');
  const [filters, setFilters] = useState({
    ...EMPTY_FILTERS,
    posted: isPostedWindow(initialPosted) ? initialPosted : '',
  });
  const navigate = useNavigate();

  const fetchOpportunities = useCallback(() => {
    setLoading(true);
    const params: Record<string, string> = { ordering: '-score' };
    if (filters.intent) params.intent = filters.intent;
    if (filters.kind) params.kind = filters.kind;
    // By default hide rejected/closed leads so the queue is what sales can act on.
    if (filters.status && filters.status !== 'all') params.status = filters.status;
    else if (!filters.status) params.actionable = 'true';
    if (filters.band) params.band = filters.band;
    if (filters.posted) params.posted = filters.posted;

    apiClient
      .get('/opportunities/', { params })
      .then((res) => {
        setRawOpportunities(res.data.results ?? res.data);
        setNextUrl(res.data.next ?? null);
      })
      .catch((err) => console.log('Error fetching opportunities:', err))
      .finally(() => setLoading(false));
  }, [filters.intent, filters.kind, filters.status, filters.band, filters.posted]);

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

  // `posted` and `kind`/`intent`/`status`/`band` are all filtered server-side
  // now (see fetchOpportunities) so they apply to the whole table, not just
  // whatever page happened to load. minScore is the one filter still worth
  // doing client-side — it only trims the current page, which is fine since
  // results already arrive ordered by score.
  const displayed = rawOpportunities.filter((o) => {
    return !(filters.minScore > 0 && o.score < filters.minScore);
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
              <option value="nonbuyer">Non-buyer</option>
              <option value="uncertain">Uncertain</option>
            </select>
          </div>
          <div className="queue-filter-field">
            <label>Kind</label>
            <select value={filters.kind} onChange={(e) => setFilters({ ...filters, kind: e.target.value })}>
              <option value="">All</option>
              {Object.entries(KIND_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div className="queue-filter-field">
            <label>Status</label>
            <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
              <option value="">Active (hides rejected)</option>
              <option value="all">All, including rejected</option>
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
            <label>Posted</label>
            <select value={filters.posted} onChange={(e) => setFilters({ ...filters, posted: e.target.value })}>
              {POSTED_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
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
                  <span className="queue-card-score">
                    Score: {item.score}
                    {formatPosted(item.source_published_at ?? item.detected_at) &&
                      ` · Posted ${formatPosted(item.source_published_at ?? item.detected_at).toLowerCase()}`}
                  </span>
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