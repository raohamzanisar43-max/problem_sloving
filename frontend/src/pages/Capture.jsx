import { useEffect, useState } from 'react'
import { captureObservation, getObservations } from '../api/client'

const EMPTY = { url: '', title: '', company: '', text: '' }

export default function Capture({ onOpenLead }) {
  const [form, setForm] = useState(EMPTY)
  const [recent, setRecent] = useState([])
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = () =>
    getObservations({ is_manual: true })
      .then((data) => setRecent((data.results || data).slice(0, 10)))
      .catch(() => {})

  useEffect(() => {
    load()
  }, [])

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    if (!form.text.trim()) {
      setError('Paste the permitted excerpt before saving.')
      return
    }
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const data = await captureObservation({ ...form, qualify: true })
      setResult(data)
      setForm(EMPTY)
      load()
    } catch (err) {
      const body = err.response?.data
      setError(body?.text?.[0] || body?.url?.[0] || body?.detail || 'Capture failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid2">
      <div className="panel">
        <h2>Capture a requirement</h2>
        <p className="sub" style={{ marginBottom: 18 }}>
          Paste the original reference and the excerpt you are permitted to retain. The
          text is scored immediately and the evidence is kept with the lead.
        </p>
        <form onSubmit={submit}>
          <div className="control">
            <label htmlFor="capture-url">Original URL</label>
            <input
              id="capture-url"
              type="url"
              placeholder="https://…"
              value={form.url}
              onChange={set('url')}
            />
          </div>
          <div className="control">
            <label htmlFor="capture-title">Title (optional)</label>
            <input id="capture-title" value={form.title} onChange={set('title')} />
          </div>
          <div className="control">
            <label htmlFor="capture-company">Company (optional)</label>
            <input id="capture-company" value={form.company} onChange={set('company')} />
          </div>
          <div className="control grow">
            <label htmlFor="capture-text">Permitted excerpt</label>
            <textarea
              id="capture-text"
              value={form.text}
              onChange={set('text')}
              placeholder="Paste only what the source licence allows you to retain…"
              style={{ minHeight: 140 }}
            />
          </div>
          {error && <p className="reason">{error}</p>}
          <button className="primary" type="submit" disabled={busy} style={{ marginTop: 12 }}>
            {busy ? 'Scoring…' : 'Capture and score'}
          </button>
        </form>

        {result && (
          <div className="evidence" style={{ marginTop: 20 }}>
            {result.opportunity ? (
              <>
                <strong>
                  Scored {result.opportunity.score} / 100 · {result.opportunity.band} ·{' '}
                  {result.opportunity.status}
                </strong>
                <p className="minor">{result.opportunity.requirement}</p>
                {(result.opportunity.review_reasons || []).length > 0 && (
                  <p className="reason">{result.opportunity.review_reasons.join(' · ')}</p>
                )}
                <button
                  className="secondary"
                  style={{ marginTop: 8 }}
                  onClick={() => onOpenLead(result.opportunity.id)}
                >
                  Open lead
                </button>
              </>
            ) : (
              <>
                <strong>Evidence stored.</strong>
                <p className="minor">
                  {result.qualification_error
                    ? `Scoring did not run: ${result.qualification_error}`
                    : 'Scoring was skipped for this capture.'}
                </p>
              </>
            )}
          </div>
        )}
      </div>

      <div className="panel">
        <h2>Recent manual captures</h2>
        {!recent.length && <div className="empty">Nothing captured yet.</div>}
        {recent.map((o) => (
          <div className="setting" key={o.id}>
            <div>
              <strong>{o.title || 'Untitled reference'}</strong>
              <p className="minor">
                {o.original_url || 'No URL'} · {(o.fetched_at || '').slice(0, 10)}
              </p>
            </div>
          </div>
        ))}
        <p className="minor" style={{ marginTop: 16 }}>
          Capture only content you are allowed to store. The excerpt is retained for the
          period set on the Settings screen.
        </p>
      </div>
    </div>
  )
}
