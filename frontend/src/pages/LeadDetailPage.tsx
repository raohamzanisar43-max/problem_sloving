import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import apiClient from '../api/apiClient';
import PageHeader from '../components/PageHeader';
import './LeadDetailPage.css';

interface Opportunity {
  id: string;
  requirement: string;
  score: number;
  band: string;
  status: string;
  revision: number;
  score_factors?: number[];
  intent?: string;
  kind?: string;
  confidence?: number;
  intent_evidence?: string;
  review_reasons?: string[];
  company_name?: string;
  company_website?: string;
  country?: string;
  budget_text?: string;
  deadline?: string;
  email?: string;
  phone?: string;
  contact_verification?: string;
  owner?: string;
  owner_name?: string;
  source_url?: string;
}

interface Me {
  id: string;
}

const FACTOR_LABELS = [
  { label: 'Buying intent', max: 30 },
  { label: 'Service match', max: 25 },
  { label: 'Recency', max: 15 },
  { label: 'Evidence quality', max: 15 },
  { label: 'Contact path', max: 10 },
  { label: 'Deadline urgency', max: 5 },
];

const BAND_COLOR_VARS: Record<string, string> = {
  Hot: '--color-band-hot',
  'High potential': '--color-band-high',
  Review: '--color-band-review',
  Archive: '--color-band-archive',
};

export default function LeadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [opp, setOpp] = useState<Opportunity | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [shareMessage, setShareMessage] = useState('');

  const loadOpportunity = useCallback(() => {
    return apiClient.get(`/opportunities/${id}/`).then((res) => setOpp(res.data));
  }, [id]);

  useEffect(() => {
    Promise.all([
      loadOpportunity(),
      apiClient.get('/me/').then((res) => setMe(res.data)),
    ])
      .catch((err) => console.log('Error loading lead detail:', err))
      .finally(() => setLoading(false));
  }, [loadOpportunity]);

  async function patchOpportunity(body: Record<string, unknown>) {
    if (!opp) return;
    setUpdating(true);
    try {
      const res = await apiClient.patch(`/opportunities/${id}/`, {
        ...body,
        expected_revision: opp.revision,
      });
      setOpp(res.data);
    } catch (err) {
      alert('Update failed. Please try again.');
      console.log('Error updating opportunity:', err);
    } finally {
      setUpdating(false);
    }
  }

  function handleAssignToMe() {
    if (!me) return;
    patchOpportunity({ owner: me.id });
  }

  function handleStatusChange(newStatus: string, label: string) {
    if (window.confirm(`Mark as ${label}? This will change the opportunity's status to "${label}".`)) {
      patchOpportunity({ status: newStatus });
    }
  }

  async function handleShare() {
    if (!opp) return;
    const lines = [
      opp.requirement ?? 'Opportunity',
      `Score: ${opp.score} · ${opp.band}`,
      opp.company_name ? `Company: ${opp.company_name}` : null,
      opp.company_website ? `Website: ${opp.company_website}` : null,
      opp.country ? `Country: ${opp.country}` : null,
      opp.budget_text ? `Budget: ${opp.budget_text}` : null,
      opp.deadline ? `Deadline: ${opp.deadline}` : null,
      opp.email ? `Email: ${opp.email}` : null,
      opp.phone ? `Phone: ${opp.phone}` : null,
      opp.source_url ? `Source: ${opp.source_url}` : null,
    ]
      .filter(Boolean)
      .join('\n');

    if (navigator.share) {
      try {
        await navigator.share({ title: opp.requirement ?? 'Novu Opportunity Radar lead', text: lines });
      } catch {
        // user cancelled, do nothing
      }
    } else {
      try {
        await navigator.clipboard.writeText(lines);
        setShareMessage('Copied to clipboard!');
        setTimeout(() => setShareMessage(''), 2500);
      } catch {
        setShareMessage('Could not copy to clipboard.');
      }
    }
  }

  if (loading) {
    return (
      <div className="lead-detail-page">
        <PageHeader title="Lead Detail" />
        <div className="lead-detail-loading">Loading...</div>
      </div>
    );
  }

  if (!opp) {
    return (
      <div className="lead-detail-page">
        <PageHeader title="Lead Detail" />
        <div className="lead-detail-loading">Opportunity load nahi hui.</div>
      </div>
    );
  }

  const bandColorVar = BAND_COLOR_VARS[opp.band] ?? '--color-text-muted';
  const factors = opp.score_factors ?? [];

  return (
    <div className="lead-detail-page">
      <PageHeader title="Lead Detail" backTo="/pipeline" />
      <div className="lead-detail-content">
        <h1 className="lead-title">{opp.requirement}</h1>

        <div className="badge-row">
          <span className="badge" style={{ background: `var(${bandColorVar})` }}>
            {opp.score} · {opp.band}
          </span>
          <span className="badge status-badge">{opp.status}</span>
        </div>

        <h2 className="section-title">Score Breakdown</h2>
        {FACTOR_LABELS.map((f, i) => (
          <div key={f.label} className="factor-row">
            <span className="factor-label">{f.label}</span>
            <div className="factor-bar-track">
              <div className="factor-bar-fill" style={{ width: `${((factors[i] ?? 0) / f.max) * 100}%` }} />
            </div>
            <span className="factor-value">
              {factors[i] ?? 0}/{f.max}
            </span>
          </div>
        ))}

        <h2 className="section-title">AI Classification</h2>
        <InfoRow label="Intent" value={opp.intent ?? '—'} />
        <InfoRow label="Kind" value={opp.kind ?? '—'} />
        <InfoRow label="Confidence" value={`${Math.round((opp.confidence ?? 0) * 100)}%`} />

        {opp.intent_evidence && (
          <div className="quote-box">
            <p className="quote-text">"{opp.intent_evidence}"</p>
          </div>
        )}

        {opp.review_reasons && opp.review_reasons.length > 0 && (
          <div className="reasons-box">
            {opp.review_reasons.map((r, idx) => (
              <span key={idx} className="reason-chip">⚠ {r}</span>
            ))}
          </div>
        )}

        <h2 className="section-title">Company</h2>
        <InfoRow label="Company" value={opp.company_name || '—'} />
        <InfoRow label="Website" value={opp.company_website || '—'} />
        <InfoRow label="Country" value={opp.country || '—'} />
        <InfoRow label="Budget" value={opp.budget_text || '—'} />
        <InfoRow label="Deadline" value={opp.deadline || '—'} />

        {(opp.email || opp.phone) && (
          <>
            <h2 className="section-title">Contact</h2>
            {opp.email && <InfoRow label="Email" value={opp.email} />}
            {opp.phone && <InfoRow label="Phone" value={opp.phone} />}
            {opp.contact_verification && <InfoRow label="Verification" value={opp.contact_verification} />}
          </>
        )}

        <h2 className="section-title">Pipeline &amp; Ownership</h2>
        <InfoRow label="Owner" value={opp.owner_name || 'Unassigned'} />
        {!opp.owner && (
          <button className="assign-button" disabled={updating} onClick={handleAssignToMe}>
            Assign to me
          </button>
        )}

        <div className="pipeline-actions-row">
          {opp.status !== 'contacted' && (
            <button
              className="pipeline-action-button"
              disabled={updating}
              onClick={() => handleStatusChange('contacted', 'Contacted')}
            >
              Mark Contacted
            </button>
          )}
          {opp.status !== 'closed' && (
            <button
              className="pipeline-action-button won"
              disabled={updating}
              onClick={() => handleStatusChange('closed', 'Closed (Won)')}
            >
              Close as Won
            </button>
          )}
          {opp.status !== 'rejected' && (
            <button
              className="pipeline-action-button lost"
              disabled={updating}
              onClick={() => handleStatusChange('rejected', 'Rejected (Lost)')}
            >
              Close as Lost
            </button>
          )}
        </div>

        {opp.source_url && (
          <a className="source-button" href={opp.source_url} target="_blank" rel="noopener noreferrer">
            Open Original Source →
          </a>
        )}

        <button className="share-button" onClick={handleShare}>
          Share Opportunity
        </button>
        {shareMessage && <p className="share-feedback">{shareMessage}</p>}
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="info-row">
      <span className="info-row-label">{label}</span>
      <span className="info-row-value">{value}</span>
    </div>
  );
}