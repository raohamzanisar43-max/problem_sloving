import { useEffect, useState } from 'react'
import { getSources } from '../api/client'
import RunHistory from './RunHistory'

function statePill(state) {
  if (['credential_required', 'account_required', 'commercial_agreement'].includes(state)) return 'review'
  if (state === 'ready') return 'hot'
  if (state === 'error') return 'closed'
  return ''
}

export default function Sources({ userRole }) {
  const [sources, setSources] = useState([])

  useEffect(() => {
    getSources().then((data) => setSources(data.results || data)).catch(console.error)
  }, [])

  return (
    <>
      <div className="panel">
        <h2>Connector readiness</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Type</th>
                <th>Planned route</th>
                <th>Access state</th>
                <th>Last live run</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.id}>
                  <td><strong>{s.name}</strong></td>
                  <td><code>{s.connector_type}</code></td>
                  <td>{s.planned_route || '—'}</td>
                  <td>
                    <span className={`pill ${statePill(s.access_state)}`}>
                      {s.access_state.replace(/_/g, ' ')}
                    </span>
                    {s.last_error && (
                      <span className="minor" style={{ marginLeft: 6 }} title={s.last_error}>⚠</span>
                    )}
                  </td>
                  <td>{s.last_success_at ? s.last_success_at.slice(0, 10) : 'None'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="panel">
        <RunHistory />
      </div>
    </>
  )
}
