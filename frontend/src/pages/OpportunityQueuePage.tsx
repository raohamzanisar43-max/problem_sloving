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
  source_url?: string;
  source_published_at?: string;
  detected_at?: string;
  budget_text?: string;
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

const STATUS_LABELS: Record<string, string> = {
  new: 'New',
  review: 'Review',
  reviewed: 'Reviewed',
  contacted: 'Contacted',
  meeting: 'Meeting',
  proposal: 'Proposal sent',
  won: 'Won',
  closed: 'Closed',
  rejected: 'Rejected',
};

const BAND_COLOR_VARS: Record<string, string> = {
  Hot: '--color-band-hot',
  'High potential': '--color-band-high',
  Review: '--color-band-review',
  Archive: '--color-band-archive',
};

const QUICK_POSTED = [
  { value: '', label: 'Any time' },
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'Last 7 days' },
  { value: 'month', label: 'Last 30 days' },
];

const EMPTY_FILTERS = {
  intent: '',
  kind: '',
  status: '',
  band: '',
  minScore: 0,
  posted: '',
  source: '',
  sort: '-posted_at',
  search: '',
};

function sourceLabel(item: Opportunity) {
  if ((item.source_url || '').includes('freelancer.com')) return 'Freelancer.com';
  return item.source_name && item.source_name !== 'example_web' ? item.source_name : 'Web';
}

export default function OpportunityQueuePage() {
  const [rawOpportunities, setRawOpportunities] = useState<Opportunity[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [nextUrl, setNextUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [searchParams] = useSearchParams();
  const initialPosted = searchParams.get('posted');
  const [filters, setFilters] = useState({
    ...EMPTY_FILTERS,
    posted: isPostedWindow(initialPosted) ? initialPosted : '',
  });
  const [searchText, setSearchText] = useState('');
  const navigate = useNavigate();

  // Search runs on the server, a moment after typing stops.
  useEffect(() => {
    const timer = window.setTimeout(() => setFilters((f) => ({ ...f, search: searchText.trim() })), 400);
    return () => window.clearTimeout(timer);
  }, [searchText]);

  const fetchOpportunities = useCallback(() => {
    setLoading(true);
    const params: Record<string, string> = { ordering: filters.sort };
    if (filters.intent) params.intent = filters.intent;
    if (filters.kind) params.kind = filters.kind;
    // By default hide rejected/closed leads so the queue is what sales can act on.
    if (filters.status && filters.status !== 'all') params.status = filters.status;
    else if (!filters.status) params.actionable = 'true';
    if (filters.band) params.band = filters.band;
    if (filters.posted) params.posted = filters.posted;
    if (filters.source) params.source = filters.source;
    if (filters.minScore > 0) params.min_score = String(filters.minScore);
    if (filters.search) params.search = filters.search;

    apiClient
      .get('/opportunities/', { params })
      .then((res) => {
        setRawOpportunities(res.data.results ?? res.data);
        setTotal(res.data.count ?? null);
        setNextUrl(res.data.next ?? null);
      })
      .catch((err) => console.log('Error fetching opportunities:', err))
      .finally(() => setLoading(false));
  }, [filters]);

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

  function clearAll() {
    setSearchText('');
    setFilters(EMPTY_FILTERS);
  }

  return (
    <div className="queue-page">
      <PageHeader title="Opportunity Queue" />
      <div className="queue-content">
        <div className="queue-quick">
          {QUICK_POSTED.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`queue-chip${filters.posted === option.value ? ' active' : ''}`}
              onClick={() => setFilters({ ...filters, posted: option.value })}
            >
              {option.label}
            </button>
          ))}
          <input
            className="queue-search"
            type="search"
            placeholder="Search title, description or company…"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
        </div>

        <div className="queue-filters">
          <div className="queue-filter-field">
            <label>Sort by</label>
            <select value={filters.sort} onChange={(e) => setFilters({ ...filters, sort: e.target.value })}>
              <option value="-posted_at">Newest first</option>
              <option value="posted_at">Oldest first</option>
              <option value="-score">Best score</option>
            </select>
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
          <div className="queue-filter-field">
            <label>Source</label>
            <select value={filters.source} onChange={(e) => setFilters({ ...filters, source: e.target.value })}>
              <option value="">All sources</option>
              <option value="freelancer">Freelancer.com projects</option>
              <option value="web">Web search leads</option>
            </select>
          </div>
          <div className="queue-filter-field">
            <label>Status</label>
            <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
              <option value="">Active (hides rejected)</option>
              <option value="all">All, including rejected</option>
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
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
          <button className="queue-clear-button" onClick={clearAll}>
            Clear all
          </button>
        </div>

        {!loading && total !== null && (
          <p className="queue-count">
            {total} {total === 1 ? 'opportunity' : 'opportunities'}
          </p>
        )}

        {loading ? (
          <div className="queue-loading">Loading...</div>
        ) : rawOpportunities.length === 0 ? (
          <p className="queue-empty">No opportunities match these filters.</p>
        ) : (
          <>
            {rawOpportunities.map((item) => {
              const posted = formatPosted(item.source_published_at ?? item.detected_at);
              return (
                <div key={item.id} className="queue-card" onClick={() => navigate(`/lead/${item.id}`)}>
                  <p className="queue-card-title">{item.requirement ?? 'Untitled'}</p>
                  <div className="queue-card-meta-row">
                    <span
                      className="queue-card-band"
                      style={{ color: `var(${BAND_COLOR_VARS[item.band] ?? '--color-text-muted'})` }}
                    >
                      {item.band}
                      {item.status && item.status !== 'new' && (
                        <span className="queue-card-status">{STATUS_LABELS[item.status] ?? item.status}</span>
                      )}
                    </span>
                    <span className="queue-card-score">
                      Score: {item.score}
                      {posted && ` · Posted ${posted.toLowerCase()}`}
                    </span>
                  </div>
                  <div className="queue-card-sub">
                    <span>{sourceLabel(item)}</span>
                    {item.budget_text && <span>Budget: {item.budget_text}</span>}
                  </div>
                </div>
              );
            })}
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
