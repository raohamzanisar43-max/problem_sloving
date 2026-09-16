import { useEffect, useState } from 'react'
import { getDuplicates, resolveDuplicate } from '../api/client'

export default function Duplicates() {
  const [candidates, setCandidates] = useState([])
  const [busy, setBusy] = useState(null)
  const [message, setMessage] = useState('')

  const load = () =>
    getDuplicates({ decision: 'pending' })
      .then((data) => setCandidates(data.results || data))
      .catch(console.error)

  useEffect(() => { load() }, [])

  const resolve = async (id, decision) => {
    setBusy(id)
    try {
      await resolveDuplicate(id, decision)
      setMessage(`Marked as ${decision}`)
      load()
    } catch (err) {
      setMessage('Action failed')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>{candidates.length} pending duplicate pair{candidates.length !== 1 ? 's' : ''}</h2>
        {message && <span className="toast">{message}</span>}
      </div>
      {!candidates.length && (
        <div className="empty">No pending duplicate candidates. Run the similarity job or wait for the next scheduled scan.</div>
      )}
      {candidates.map((c) => (
        <div key={c.id} className="panel" style={{ marginBottom: 16 }}>
          <div className="grid2">
            <div>
              <small className="minor">Opportunity A · score {c.opportunity_a?.score ?? '—'}</small>
              <p><strong>{c.opportunity_a?.requirement}</strong></p>
              <p className="minor">{c.opportunity_a?.company_name || 'Unknown company'} · {c.opportunity_a?.band}</p>
            </div>
            <div>
              <small className="minor">Opportunity B · score {c.opportunity_b?.score ?? '—'}</small>
              <p><strong>{c.opportunity_b?.requirement}</strong></p>
              <p className="minor">{c.opportunity_b?.company_name || 'Unknown company'} · {c.opportunity_b?.band}</p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 12, alignItems: 'center' }}>
            <span className="tag">Similarity {(c.similarity * 100).toFixed(0)}%</span>
            <button
              className="primary"
              disabled={busy === c.id}
              onClick={() => resolve(c.id, 'accepted')}
            >
              Merge (keep higher score)
            </button>
            <button
              className="secondary"
              disabled={busy === c.id}
              onClick={() => resolve(c.id, 'rejected')}
            >
              Keep both
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

