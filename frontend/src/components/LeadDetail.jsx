import { useEffect, useState } from 'react'
import {
  createDraft,
  getActivities,
  getContacts,
  getDrafts,
  getOpportunity,
  getUsers,
  updateOpportunity,
} from '../api/client'

const DRAFTABLE = ['reviewed', 'contacted', 'meeting', 'proposal', 'won']

export default function LeadDetail({ leadId, onClose, onSaved }) {
  const [lead, setLead] = useState(null)
  const [users, setUsers] = useState([])
  const [activities, setActivities] = useState([])
  const [contacts, setContacts] = useState([])
  const [drafts, setDrafts] = useState([])
  const [status, setStatus] = useState('')
  const [owner, setOwner] = useState('')
  const [notes, setNotes] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [drafting, setDrafting] = useState(false)
  const [copied, setCopied] = useState(false)

  const loadLead = () =>
    getOpportunity(leadId).then((data) => {
      setLead(data)
      setStatus(data.status)
      setOwner(data.owner || '')
      setNotes(data.notes || '')
      return data
    })

  const loadSidecars = () => {
    getActivities(leadId).then(setActivities).catch(() => {})
    getDrafts(leadId).then(setDrafts).catch(() => {})
    getContacts({ opportunity: leadId })
      .then((data) => setContacts(data.results || data))
      .catch(() => {})
  }

  useEffect(() => {
    loadLead()
    loadSidecars()
    getUsers()
      .then((data) => setUsers(data.results || data))
      .catch(() => setMessage('Could not load the assignment list.'))
  }, [leadId])

  const save = async () => {
    setBusy(true)
    try {
      const updated = await updateOpportunity(leadId, {
        status,
        owner: owner || null,
        notes,
        expected_revision: lead.revision,
      })
      setLead(updated)
      setMessage('Saved: Status and assignment updated.')
      loadSidecars()
      onSaved?.()
    } catch (err) {
      setMessage(err.response?.data?.expected_revision?.[0] || 'Save failed')
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
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!lead) {
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div className="detail" onClick={(e) => e.stopPropagation()}>
          <div className="dialog-top">
            <p>Loading details…</p>
            <button className="close" onClick={onClose}>×</button>
          </div>
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
    <div className="modal-backdrop" onClick={onClose}>
      <div className="detail" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-top">
          <div>
            <div className="minor">
              OPPORTUNITY / <strong>{lead.id || lead.public_id}</strong> · Revision #{lead.revision || 1}
            </div>
            <h2 style={{ margin: '6px 0 0', fontSize: 20 }}>{lead.requirement}</h2>
          </div>
          <button className="close" onClick={onClose} aria-label="Close">×</button>
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

            <h3 style={{ marginTop: 20 }}>Fact Provenance & Verification</h3>
            <div className="facts">
              {[
                ['Company', lead.company_name || 'Unknown'],
                ['Country', lead.country || 'Unknown'],
                ['Budget', lead.budget_text || 'None published'],
                ['Published', (lead.source_published_at || lead.detected_at || '').slice(0, 10) || '—'],
                ['Email', lead.email || 'Unavailable'],
                ['Verification', lead.contact_verification ? `${lead.contact_verification} · not mailbox verified` : 'Unavailable'],
                ['Deadline', lead.deadline || 'None quoted'],
                ['Evidence Path', lead.email ? 'Direct published business email' : 'Original source reference'],
              ].map(([k, v]) => (
                <div className="fact" key={k}>
                  <small>{k}</small>
                  <span>{v}</span>
                </div>
              ))}
            </div>

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
