import { useEffect, useState } from 'react'
import { getRuns, triggerRun, getSources } from '../api/client'

const STATE_COLOR = {
  completed: 'hot',
  partial: 'review',
  failed: 'closed',
  running: 'review',
  queued: '',
}

export default function RunHistory({ sourceId, compact }) {
  const [runs, setRuns] = useState([])
  const [sources, setSources] = useState([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const load = () => {
    const params = sourceId ? { source: sourceId } : {}
    getRuns(params).then((d) => setRuns(d.results || d)).catch(console.error)
  }

  useEffect(() => {
    load()
    if (!compact) getSources().then((d) => setSources(d.results || d)).catch(console.error)
  }, [sourceId])

  const trigger = async (sid) => {
    setBusy(true)
    try {
      await triggerRun(sid)
      setMsg('Run queued')
      setTimeout(load, 1500)
    } catch {
      setMsg('Failed to queue run')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      {!compact && (
        <div className="panel-head" style={{ marginBottom: 12 }}>
          <h2>Collection run history</h2>
          {msg && <span className="toast">{msg}</span>}
        </div>
      )}
      {!compact && sources.length > 0 && (
        <div className="controls" style={{ marginBottom: 16 }}>
          {sources.filter((s) => s.enabled || s.access_state === 'ready').map((s) => (
            <button
              key={s.id}
              className="secondary"
              disabled={busy}
              onClick={() => trigger(s.id)}
            >
              Run {s.name}
            </button>
          ))}
        </div>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Source</th>
              <th>Trigger</th>
              <th>State</th>
              <th>Fetched</th>
              <th>New</th>
              <th>Errors</th>
              <th>Spend</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>
            {!runs.length && (
              <tr><td colSpan={8} className="empty">No runs yet. Trigger a manual run above or wait for the scheduler.</td></tr>
            )}
            {runs.map((r) => (
              <tr key={r.id}>
                <td>{r.source_name || '—'}</td>
                <td>{r.trigger}</td>
                <td><span className={`pill ${STATE_COLOR[r.state] || ''}`}>{r.state}</span></td>
                <td>{r.counters?.fetched ?? '—'}</td>
                <td>{r.counters?.new ?? '—'}</td>
                <td>{r.counters?.errors ?? 0}</td>
                <td>${parseFloat(r.estimated_spend || 0).toFixed(4)}</td>
                <td>{r.started_at ? r.started_at.slice(0, 16).replace('T', ' ') : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

