import { useEffect, useState } from 'react'
import { getSources, updateSource } from '../api/client'
import RunHistory from './RunHistory'

function statePill(state) {
  if (['credential_required', 'account_required', 'commercial_agreement'].includes(state)) return 'review'
  if (state === 'ready') return 'hot'
  if (state === 'error') return 'closed'
  return ''
}

export default function Sources({ userRole }) {
  const [sources, setSources] = useState([])
  const [savingId, setSavingId] = useState(null)
  const [message, setMessage] = useState(null)

  const load = () => getSources().then((data) => setSources(data.results || data)).catch(console.error)

  useEffect(() => { load() }, [])

  const toggleSource = async (source) => {
    setSavingId(source.id)
    setMessage(null)
    try {
      const updated = await updateSource(source.id, { enabled: !source.enabled })
      setSources((items) => items.map((item) => item.id === updated.id ? updated : item))
      setMessage({ type: 'success', text: `${updated.name} is now ${updated.enabled ? 'enabled' : 'disabled'}.` })
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Could not update this source.' })
    } finally {
      setSavingId(null)
    }
  }

  return (
    <>
      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Connector readiness</h2>
            <p className="minor">{userRole === 'admin' ? 'Enable only connectors with approved credentials and access.' : 'Only administrators can enable or disable connectors.'}</p>
          </div>
          {message && <span className={message.type === 'error' ? 'error-message' : 'toast'} role="status">{message.text}</span>}
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Type</th>
                <th>Planned route</th>
                <th>Access state</th>
                <th>Last live run</th>
                <th>Collection</th>
              </tr>
            </thead>
            <tbody>
              {!sources.length && <tr><td colSpan={6} className="empty">No connectors have been configured yet.</td></tr>}
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
                  <td>
                    {userRole === 'admin' ? (
                      <button
                        type="button"
                        className={s.enabled ? 'secondary' : 'primary'}
                        disabled={savingId === s.id || (s.access_state !== 'ready' && !s.enabled)}
                        title={s.access_state !== 'ready' && !s.enabled ? 'Configure approved access before enabling this connector.' : undefined}
                        onClick={() => toggleSource(s)}
                      >
                        {savingId === s.id ? 'Saving…' : s.enabled ? 'Disable' : 'Enable'}
                      </button>
                    ) : (
                      <span className={`pill ${s.enabled ? 'pill-reviewed' : 'pill-closed'}`}>
                        {s.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    )}
                  </td>
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
