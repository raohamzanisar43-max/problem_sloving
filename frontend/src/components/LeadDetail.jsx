import { useEffect, useState } from 'react'
import {
  createDraft,
  getActivities,
  getContacts,
  getDrafts,
  getOpportunity,
  getUsers,
  SUPPORTED_CATEGORIES,
  updateOpportunity,
} from '../api/client'

const DRAFTABLE = ['reviewed', 'contacted', 'meeting', 'proposal', 'won']

// Extracted facts a sales user may correct by hand. Keep in step with
// EDITABLE_DETAIL_FIELDS in the opportunities serializer.
const DETAIL_FIELDS = [
  ['requirement', 'Requirement'],
  ['primary_category', 'Service category'],
  ['company_name', 'Company'],
  ['company_domain', 'Company domain'],
  ['country', 'Country'],
  ['industry', 'Industry'],
  ['budget_text', 'Budget'],
  ['deadline', 'Deadline', 'date'],
  ['contact_name', 'Contact name'],
  ['contact_designation', 'Contact designation'],
  ['email', 'Email', 'email'],
  ['phone', 'Phone', 'tel'],
]

const detailsFrom = (data) =>
  Object.fromEntries(DETAIL_FIELDS.map(([key]) => [key, data[key] || '']))

export default function LeadDetail({ leadId, onClose, onSaved }) {
  const [lead, setLead] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [users, setUsers] = useState([])
  const [activities, setActivities] = useState([])
  const [contacts, setContacts] = useState([])
  const [drafts, setDrafts] = useState([])
  const [status, setStatus] = useState('')
  const [owner, setOwner] = useState('')
  const [notes, setNotes] = useState('')
  const [details, setDetails] = useState({})
  const [editing, setEditing] = useState(false)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [drafting, setDrafting] = useState(false)
  const [copied, setCopied] = useState(false)

  const loadLead = () =>
    getOpportunity(leadId).then((data) => {
      setLead(data)
      setLoadError('')
      setStatus(data.status)
      setOwner(data.owner || '')
      setNotes(data.notes || '')
      setDetails(detailsFrom(data))
      setEditing(false)
      return data
    }).catch((err) => {
      setLoadError(err.response?.data?.detail || 'Could not load this opportunity.')
    })

  const loadSidecars = () => {
    getActivities(leadId).then(setActivities).catch(() => {})
    getDrafts(leadId).then(setDrafts).catch(() => {})
    getContacts({ opportunity: leadId })
      .then((data) => setContacts(data.results || data))
      .catch(() => {})
  }

  useEffect(() => {
    setLead(null)
    setLoadError('')
    loadLead()
    loadSidecars()
    getUsers()
      .then((data) => setUsers(data.results || data))
      .catch(() => setMessage('Could not load the assignment list.'))
  }, [leadId])

  useEffect(() => {
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  const save = async () => {
    setBusy(true)
    try {
      const updated = await updateOpportunity(leadId, {
        status,
        owner: owner || null,
        notes,
        ...(editing ? { ...details, deadline: details.deadline || null } : {}),
        expected_revision: lead.revision,
      })
      setLead(updated)
      setDetails(detailsFrom(updated))
      setEditing(false)
      setMessage('Saved: Lead updated.')
      loadSidecars()
      onSaved?.()
    } catch (err) {
      const body = err.response?.data || {}
      const fieldError = DETAIL_FIELDS.find(([key]) => body[key])
      setMessage(
        body.expected_revision?.[0] ||
          (fieldError ? `${fieldError[1]}: ${body[fieldError[0]][0]}` : 'Save failed')
      )
    } finally {
      setBusy(false)
    }
  }

  const writeDraft = async () => {
    setDrafting(true)
    try {
      await createDraft(leadId)
      setMessage('Draft generated for review. Nothing was sent externally.')
      loadSidecars()
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Could not prepare draft.')
    } finally {
      setDrafting(false)
    }
  }

  const copyDraft = (text) => {
    if (!navigator.clipboard?.writeText) {
      setMessage('Copy is unavailable in this browser. Select the draft text and copy it manually.')
      return
    }
    navigator.clipboard.writeText(text)
      .then(() => {
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      })
      .catch(() => setMessage('Copy failed. Select the draft text and copy it manually.'))
  }

  if (!lead) {
    return (
      <div className="modal-backdrop" onClick={onClose} role="presentation">
        <div className="detail" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Opportunity details">
          <div className="dialog-top">
            <p>{loadError || 'Loading details…'}</p>
            <button type="button" className="close" onClick={onClose} aria-label="Close">×</button>
          </div>
          {loadError && <div className="dialog-content"><button type="button" className="secondary" onClick={loadLead}>Try again</button></div>}
        </div>
      </div>
    )
  }

  const breakdown = lead.score_breakdown || [
    { factor: 'Buying intent', score: lead.score_factors?.[0] ?? 30, max: 30 },
    { factor: 'Service match', score: lead.score_factors?.[1] ?? 25, max: 25 },
    { factor: 'Recency', score: lead.score_factors?.[2] ?? 15, max: 15 },
    { factor: 'Evidence quality', score: lead.score_factors?.[3] ?? 15, max: 15 },
    { factor: 'Contact path', score: lead.score_factors?.[4] ?? 10, max: 10 },
    { factor: 'Deadline urgency', score: lead.score_factors?.[5] ?? 0, max: 5 },
  ]
  const canDraft = DRAFTABLE.includes(status || lead.status)

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div className="detail" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Opportunity details">
        <div className="dialog-top">
          <div>
            <div className="minor">
              OPPORTUNITY / <strong>{lead.id || lead.public_id}</strong> · Revision #{lead.revision || 1}
            </div>
            <h2 style={{ margin: '6px 0 0', fontSize: 20 }}>{lead.requirement}</h2>
          </div>
          <button type="button" className="close" onClick={onClose} aria-label="Close">×</button>
        </div>

        <div className="dialog-content">
          {/* Left Column: Requirement, Evidence, Provenance Facts, Notes */}
          <div>
            <h3>Retained Source Evidence</h3>
            <div className="evidence">
              <div className="evidence-badge">
                <span className="dot online"></span> Exact Retained Excerpt
              </div>
              <p style={{ margin: '8px 0 0', fontStyle: 'normal' }}>
                "{lead.text}"
              </p>
            </div>
            
            {lead.source_url && (
              <div style={{ marginTop: 8 }}>
                <a
                  href={lead.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="source-link"
                >
                  ↗ Original Reference: {lead.source_url}
                </a>
              </div>
            )}

            <div className="facts-heading">
              <h3>Fact Provenance & Verification</h3>
              <button
                type="button"
                className="secondary"
                style={{ fontSize: 12, padding: '4px 10px' }}
                onClick={() => {
                  if (editing) setDetails(detailsFrom(lead))
                  setEditing(!editing)
                }}
              >
                {editing ? 'Cancel edit' : 'Edit details'}
              </button>
            </div>
            {editing ? (
            <div className="facts">
              {DETAIL_FIELDS.map(([key, label, type]) => (
                <div className={`fact${key === 'requirement' ? ' fact-wide' : ''}`} key={key}>
                  <label htmlFor={`lead-${key}`}><small>{label}</small></label>
                  {key === 'primary_category' ? (
                    <select
                      id={`lead-${key}`}
                      value={details[key]}
                      onChange={(e) => setDetails({ ...details, [key]: e.target.value })}
                    >
                      <option value="">None</option>
                      {SUPPORTED_CATEGORIES.map((c) => (
                        <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      id={`lead-${key}`}
                      type={type || 'text'}
                      value={details[key]}
                      onChange={(e) => setDetails({ ...details, [key]: e.target.value })}
                    />
                  )}
                </div>
              ))}
              <p className="minor fact-wide">
                Changes are saved with "Save Changes" and recorded in the activity timeline.
                The score is not recalculated.
              </p>
            </div>
            ) : (
            <div className="facts">
              {[
                ['Company', lead.company_name || 'Unknown'],
                ['Contact', [lead.contact_name, lead.contact_designation].filter(Boolean).join(' · ') || 'Unknown'],
                ['Phone', lead.phone || 'Unavailable'],
                ['Country', lead.country || 'Unknown'],
                ['Budget', lead.budget_text || 'None published'],
                ['Published', (lead.source_published_at || lead.detected_at || '').slice(0, 10) || '—'],
                ['Email', lead.email || 'Unavailable'],
                ['Verification', lead.contact_verification === 'manual'
                  ? 'Entered manually · not from source'
                  : lead.contact_verification ? `${lead.contact_verification} · not mailbox verified` : 'Unavailable'],
                ['Deadline', lead.deadline || 'None quoted'],
                ['Evidence Path', lead.email && lead.contact_verification !== 'manual' ? 'Direct published business email' : 'Original source reference'],
              ].map(([k, v]) => (
                <div className="fact" key={k}>
                  <small>{k}</small>
                  <span>{v}</span>
                </div>
              ))}
            </div>
            )}

            {contacts.length > 0 && (
              <>
                <h3 style={{ marginTop: 20 }}>Published Contacts with Provenance</h3>
                {contacts.map((c) => (
                  <div className="setting" key={c.id}>
                    <div>
                      <strong>{c.email || c.phone || c.name || 'Contact'}</strong>
                      <p className="minor">
                        {c.name || 'Company Contact'}
                        {c.designation ? ` · ${c.designation}` : ''}
                      </p>
                    </div>
                    <span className="pill pill-reviewed">{c.verification_state || 'published'}</span>
                  </div>
                ))}
              </>
            )}

            <h3 style={{ marginTop: 20 }}>Review Reasons & Qualification Flags</h3>
            {lead.review_reasons && lead.review_reasons.length > 0 ? (
              <div className="review-box">
                {lead.review_reasons.map((r, i) => (
                  <div key={i} className="review-item">
                    ⚠️ {r}
                  </div>
                ))}
              </div>
            ) : (
              <p className="reason" style={{ color: '#059669', background: '#ecfdf5', padding: '10px 14px', borderRadius: 6 }}>
                ✓ No review flags detected. All evidence criteria met.
              </p>
            )}

            <h3 style={{ marginTop: 20 }}>Sales Follow-up & Activity Notes</h3>
            <label className="minor" htmlFor="lead-note">Internal Strategy Note</label>
            <textarea
              id="lead-note"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Record outreach progress, qualification notes, next steps…"
              rows={3}
            />
          </div>

          {/* Right Column: Score Breakdown, Status, Owner, Sales Draft, History */}
          <div>
            <div className="score-header-box">
              <div>
                <span className="minor">Deterministic Qualification Score</span>
                <div style={{ fontSize: 26, fontWeight: 700, color: '#0f2942' }}>
                  {lead.score} <span style={{ fontSize: 16, color: '#64748b' }}>/ 100</span>
                </div>
              </div>
              <span className={`band-tag band-${(lead.band || 'hot').toLowerCase().replace(/\s+/g, '-')}`}>
                {lead.band}
              </span>
            </div>

            <div className="breakdown" style={{ marginTop: 16 }}>
              {breakdown.map((f, i) => {
                const label = f.label || f.factor || `Factor ${i + 1}`
                const pts = f.points ?? f.score ?? 0
                const max = f.max || 30
                const pct = Math.min(100, Math.round((pts / max) * 100))
                return (
                  <div className="factor" key={label}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                      <span>{label}</span>
                      <strong>{pts} / {max}</strong>
                    </div>
                    <div className="bar">
                      <span style={{ width: `${pct}%` }} />
                    </div>
                    {f.explanation && <small className="minor">{f.explanation}</small>}
                  </div>
                )
              })}
            </div>

            <div className="controls" style={{ marginTop: 20 }}>
              <div className="control grow">
                <label htmlFor="lead-status">Sales Pipeline Status</label>
                <select id="lead-status" value={status} onChange={(e) => setStatus(e.target.value)}>
                  <option value="new">New</option>
                  <option value="review">Review Required</option>
                  <option value="reviewed">Reviewed</option>
                  <option value="contacted">Contacted</option>
                  <option value="meeting">Meeting Scheduled</option>
                  <option value="proposal">Proposal Submitted</option>
                  <option value="won">Won / Closed Won</option>
                  <option value="rejected">Rejected (Non-buyer)</option>
                  <option value="closed">Closed (Expired)</option>
                </select>
              </div>
              <div className="control grow">
                <label htmlFor="lead-owner">Assigned Sales Owner</label>
                <select id="lead-owner" value={owner} onChange={(e) => setOwner(e.target.value)}>
                  <option value="">Unassigned</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.display_name || u.username} ({u.role})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Outreach Draft Section */}
            <div className="draft-section" style={{ marginTop: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0 }}>Tailored Outreach Draft</h3>
                <button
                  className="secondary"
                  onClick={writeDraft}
                  disabled={drafting || !canDraft}
                  title={canDraft ? undefined : 'Move status to "reviewed" first.'}
                  style={{ fontSize: 12, padding: '6px 12px' }}
                >
                  {drafting ? 'Generating…' : 'Generate Outreach Draft'}
                </button>
              </div>
              
              {!canDraft && (
                <p className="minor" style={{ marginTop: 6, color: '#94a3b8' }}>
                  ℹ️ Outreach drafts can be generated once the lead has been moved to "Reviewed" status.
                </p>
              )}

              {drafts.length > 0 && drafts.map((d) => (
                <div className="draft-card" key={d.id}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span className="tag" style={{ fontSize: 11 }}>Prepared by Novu Intelligence · Never auto-sent</span>
                    <button
                      className="secondary"
                      style={{ fontSize: 11, padding: '3px 8px' }}
                      onClick={() => copyDraft(d.content)}
                    >
                      {copied ? '✓ Copied' : 'Copy Message'}
                    </button>
                  </div>
                  <pre className="draft-text">{d.content}</pre>
                </div>
              ))}
            </div>

            {/* Activity History */}
            <h3 style={{ marginTop: 24 }}>Activity & Audit Timeline</h3>
            <div className="activity-timeline">
              {activities.length === 0 ? (
                <p className="minor">No activity history recorded yet.</p>
              ) : (
                activities.slice(0, 5).map((a) => (
                  <div className="activity-item" key={a.id}>
                    <span className="dot online"></span>
                    <div>
                      <strong>{(a.kind || a.action || 'update').replace(/_/g, ' ')}</strong>
                      <span className="minor" style={{ marginLeft: 8 }}>
                        by {a.actor_name || 'System'}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="dialog-footer">
          <span className="toast" id="detail-message">{message}</span>
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="secondary" onClick={onClose}>Close</button>
            <button className="primary" onClick={save} disabled={busy}>
              {busy ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
