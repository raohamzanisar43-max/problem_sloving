import { useState } from 'react'
import { login, getMe } from '../api/client'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(username, password)
      const me = await getMe()
      onLogin(me)
    } catch (err) {
      setError('Invalid credentials. Try admin / admin123 after running seed_demo.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={submit}>
        <div className="brand" style={{ color: '#183044', marginBottom: 20 }}>
          novu<span style={{ color: '#1769a3' }}>.</span>
          <small style={{ color: '#5d7284' }}>Opportunity Radar</small>
        </div>
        <h1>Sign in</h1>
        <p className="sub" style={{ marginBottom: 20 }}>Sales intelligence workspace</p>
        {error && <div className="error">{error}</div>}
        <div className="field">
          <label htmlFor="username">Username</label>
          <input
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>
        <button className="primary" type="submit" disabled={busy} style={{ width: '100%' }}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="hint">
          Demo accounts (after <code>python manage.py seed_demo</code>):<br />
          admin / admin123<br />
          manager / manager123<br />
          executive / exec123
        </p>
      </form>
    </div>
  )
}
