import { useEffect, useState } from 'react'
import { createSyncJob, downloadCsv, getSyncJobs, getSyncTargets } from '../api/client'

const STATE_COLOR = {
  completed: 'hot',
  skipped: 'review',
  failed: 'closed',
  running: 'review',
  queued: '',
}

export default function Exports() {
  const [jobs, setJobs] = useState([])
  const [targets, setTargets] = useState([])
  const [target, setTarget] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  const load = () => {
    getSyncJobs()
      .then((data) => setJobs((data.results || data).slice(0, 10)))
      .catch(() => {})
    getSyncTargets()
      .then((data) => setTargets((data.results || data).filter((t) => t.enabled)))
      .catch(() => {})
  }

  useEffect(() => {
    load()
  }, [])

  const sync = async () => {
    setBusy(true)
    setMessage('')
    try {
      const job = await createSyncJob(target || null)
      setMessage(
        job.state === 'completed'
          ? `Wrote ${job.counters?.rows_written ?? 0} rows to the workbook.`
          : job.error || `Job ${job.state}.`
      )
      load()
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Could not queue the sync job.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid2">
      <div className="panel">
        <h2>Excel compatible snapshot</h2>
        <p className="sub">
          Download the filtered queue with original references, requirements, contact
          evidence, scores and sales status.
        </p>
        <div className="setting">
          <div>
            <strong>Format</strong>
            <p>UTF 8 CSV with fixed headers and formula safe text.</p>
          </div>
          <span className="pill">CSV</span>
        </div>
        <div className="setting">
          <div>
            <strong>Data authority</strong>
            <p>Production PostgreSQL; CSV is a reporting snapshot.</p>
          </div>
        </div>
        <button className="primary" style={{ marginTop: 20 }} onClick={() => downloadCsv()}>
          Download filtered CSV
        </button>
      </div>

      <div className="panel">
        <div className="panel-head">
          <h2>Cloud workbook sync</h2>
          {message && <span className="toast">{message}</span>}
        </div>
        <div className="controls" style={{ marginBottom: 12 }}>
          <div className="control grow">
            <label htmlFor="sync-target">Destination</label>
            <select id="sync-target" value={target} onChange={(e) => setTarget(e.target.value)}>
              <option value="">Default workbook</option>
              {targets.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <button className="primary" onClick={sync} disabled={busy}>
            {busy ? 'Running…' : 'Run sync now'}
          </button>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Destination</th>
                <th>State</th>
                <th>Rows</th>
                <th>Started</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {!jobs.length && (
                <tr>
                  <td colSpan={5} className="empty">
                    No sync jobs yet.
                  </td>
                </tr>
              )}
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td>{j.target_name || 'Default workbook'}</td>
                  <td>
                    <span className={`pill ${STATE_COLOR[j.state] || ''}`}>{j.state}</span>
                  </td>
                  <td>{j.counters?.rows_written ?? '—'}</td>
                  <td>{(j.created_at || '').slice(0, 16).replace('T', ' ')}</td>
                  <td className="minor">{j.error || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="sub" style={{ marginTop: 12 }}>
          Microsoft Graph table-row sync needs a delegated sign in and a named workbook
          table. Until those are configured, jobs are recorded as skipped with the reason.
        </p>
      </div>
    </div>
  )
}
