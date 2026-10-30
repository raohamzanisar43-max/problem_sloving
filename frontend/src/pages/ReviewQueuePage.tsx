import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';
import PageHeader from '../components/PageHeader';
import './ReviewQueuePage.css';

interface Opportunity {
  id: string;
  requirement: string;
  score: number;
  band: string;
  intent?: string;
  confidence?: number;
  review_reasons?: string[];
}

const INTENT_LABELS = [
  { label: 'Buyer', value: 'buyer' },
  { label: 'Hiring', value: 'hiring' },
  { label: 'Non-buyer', value: 'nonbuyer' },
  { label: 'Uncertain', value: 'uncertain' },
];

export default function ReviewQueuePage() {
  const [items, setItems] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<string | null>(null);
  const navigate = useNavigate();

  const loadReviewQueue = useCallback(() => {
    apiClient
      .get('/opportunities/', { params: { status: 'review' } })
      .then((res) => setItems(res.data.results ?? res.data))
      .catch((err) => console.log('Error loading review queue:', err))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadReviewQueue();
  }, [loadReviewQueue]);

  async function handleAction(id: string, newStatus: 'new' | 'rejected') {
    setActingId(id);
    try {
      const detail = await apiClient.get(`/opportunities/${id}/`);
      await apiClient.patch(`/opportunities/${id}/`, {
        status: newStatus,
        expected_revision: detail.data.revision,
      });
      setItems((prev) => prev.filter((o) => o.id !== id));
    } catch (err) {
      alert('Update failed. Please try again.');
      console.log('Error updating review item:', err);
    } finally {
      setActingId(null);
    }
  }

  return (
    <div className="review-page">
      <PageHeader title="Review Queue" />
      <div className="review-content">
        {loading ? (
          <div className="review-loading">Loading...</div>
        ) : items.length === 0 ? (
          <p className="review-empty">No opportunities pending review.</p>
        ) : (
          items.map((item) => (
            <div key={item.id} className="review-card">
              <div className="review-card-info">
                <p className="review-card-title" onClick={() => navigate(`/lead/${item.id}`)}>
                  {item.requirement ?? 'Untitled'}
                </p>
                <p className="review-card-meta">
                  {item.band} · Score {item.score} · AI confidence {Math.round((item.confidence ?? 0) * 100)}%
                </p>
                <div className="review-intent-row">
                  {INTENT_LABELS.map((opt) => (
                    <span
                      key={opt.value}
                      className={`review-intent-chip${item.intent === opt.value ? ' active' : ''}`}
                    >
                      {opt.label}
                    </span>
                  ))}
                </div>
                {item.review_reasons && item.review_reasons.length > 0 && (
                  <div className="review-reasons-row">
                    {item.review_reasons.map((r, i) => (
                      <span key={i} className="review-reason-chip">{r}</span>
                    ))}
                  </div>
                )}
              </div>
              <div className="review-card-actions">
                <button
                  className="review-reject-button"
                  disabled={actingId === item.id}
                  onClick={() => handleAction(item.id, 'rejected')}
                >
                  Reject
                </button>
                <button
                  className="review-approve-button"
                  disabled={actingId === item.id}
                  onClick={() => handleAction(item.id, 'new')}
                >
                  {actingId === item.id ? 'Working...' : 'Approve'}
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}