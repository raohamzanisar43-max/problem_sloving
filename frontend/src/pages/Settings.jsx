import { useEffect, useState } from 'react'
import { getSettings, updateSettings } from '../api/client'

function SettingRow({ item, draft, editable, onChange }) {
  const value = draft[item.key] !== undefined ? draft[item.key] : item.value
  const inputId = `setting-${item.key}`

  return (
    <div className="setting">
      <div>
        <strong>
          <label htmlFor={editable && item.editable ? inputId : undefined}>{item.label}</label>
        </strong>
        <p>{item.description}</p>
      </div>
      {editable && item.editable ? (
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input
            id={inputId}
            type={item.type === 'str' ? 'text' : 'number'}
            step={item.type === 'float' ? '0.05' : '1'}
            min={item.min ?? undefined}
            max={item.max ?? undefined}
            value={value ?? ''}
            onChange={(e) => onChange(item.key, e.target.value)}
            style={{ width: item.type === 'str' ? 220 : 90 }}
          />
          {item.unit && <span className="minor">{item.unit}</span>}
        </span>
      ) : (
        <span className={item.editable ? 'tag' : 'pill'}>
          {String(value === '' || value === null ? 'Not configured' : value)}
          {item.unit ? ` ${item.unit}` : ''}
        </span>
      )}
    </div>
  )
}

export default function Settings() {
  const [items, setItems] = useState([])
  const [editable, setEditable] = useState(false)
  const [provider, setProvider] = useState(null)
  const [draft, setDraft] = useState({})
  const [message, setMessage] = useState('')
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)

  const load = () =>
    getSettings()
      .then((data) => {
        setItems(data.settings || [])
        setEditable(Boolean(data.editable))
        setProvider(data.provider || null)
      })
      .catch(() => setMessage('Could not load settings.'))

  useEffect(() => {
    load()
  }, [])

  const change = (key, value) => {
    setDraft((prev) => ({ ...prev, [key]: value }))
    setMessage('')
  }

  const save = async () => {
    if (!Object.keys(draft).length) return
    setBusy(true)
    setErrors({})
    try {
      const data = await updateSettings(draft)
      setItems(data.settings || [])
      setDraft({})
      setMessage(`Saved: ${(data.updated || []).join(', ')}`)
    } catch (err) {
      const body = err.response?.data
      setErrors(body?.errors || {})
      setMessage(body?.detail || 'Save failed.')
    } finally {
      setBusy(false)
    }
  }

  const dirty = Object.keys(draft).length > 0

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>Operating settings</h2>
        {message && <span className="toast">{message}</span>}
      </div>
      <p className="sub" style={{ marginBottom: 18 }}>
        {editable
          ? 'These are the values this deployment is running. Changes take effect immediately.'
          : 'These are the values this deployment is running. Only an administrator can change them.'}
      </p>

      {provider && (
        <div className="setting">
          <div>
            <strong>Extraction provider status</strong>
            <p>
              {provider.degraded
                ? `Configured as "${provider.configured}" but running the offline stub — install the provider SDK and set its API key.`
                : `Running the "${provider.active}" provider.`}
            </p>
          </div>
          <span className={`pill ${provider.degraded ? 'review' : ''}`}>
            {provider.degraded ? 'Degraded' : 'Healthy'}
          </span>
        </div>
      )}

      {!items.length && <div className="empty">Loading settings…</div>}

      {items.map((item) => (
        <div key={item.key}>
          <SettingRow item={item} draft={draft} editable={editable} onChange={change} />
          {errors[item.key] && (
            <p className="reason" style={{ marginTop: -8 }}>{errors[item.key]}</p>
          )}
        </div>
      ))}

      {editable && (
        <div style={{ display: 'flex', gap: 8, marginTop: 20 }}>
          <button className="primary" onClick={save} disabled={!dirty || busy}>
            {busy ? 'Saving…' : 'Save changes'}
          </button>
          <button className="secondary" onClick={() => { setDraft({}); setErrors({}); setMessage('') }} disabled={!dirty}>
            Discard
          </button>
        </div>
      )}

      <p className="minor" style={{ marginTop: 20 }}>
        Credentials are never stored here. API keys and connector secrets live in the
        environment or secret store.
      </p>
    </div>
  )
}
