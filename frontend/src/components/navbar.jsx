import { useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getDuplicateCount, USERS, switchUserRole } from '../api/client'

const NAV = [
  { path: '/', label: 'Overview', icon: '📊' },
  { path: '/opportunities', label: 'Opportunities Queue', icon: '🎯' },
  { path: '/capture', label: 'Manual Capture', icon: '📥' },
  { path: '/pipeline', label: 'Sales Pipeline', icon: '📋' },
  { path: '/duplicates', label: 'Duplicate Review', icon: '🔍' },
  { path: '/sources', label: 'Source Health', icon: '📡' },
  { path: '/rules', label: 'Search Rules', icon: '⚙️' },
  { path: '/exports', label: 'Exports & Sync', icon: '📁' },
  { path: '/settings', label: 'Settings', icon: '🛠️' },
]

const META = {
  '/': ['Opportunity Overview', 'Find the requirement. Keep the evidence. Give sales a clear next step.'],
  '/opportunities': ['Opportunity Queue', 'Review source evidence, qualify the buyer and assign the next action.'],
  '/capture': ['Manual Capture Desk', 'Paste a permitted excerpt and its original reference to score it immediately.'],
  '/sources': ['Connector Health & Observability', 'Monitor only the channels that are configured and accessible.'],
  '/rules': ['Search Rules & Policy', 'Define services, buying signals, and deterministic qualification policies.'],
  '/pipeline': ['Sales Pipeline Stages', 'Move reviewed opportunities through qualified sales stages.'],
  '/duplicates': ['Duplicate Review', 'Resolve near-duplicate opportunity pairs detected by the similarity scanner.'],
  '/exports': ['Exports & Cloud Sync', 'Download formula-safe CSV or view cloud workbook synchronization.'],
  '/settings': ['Operating Settings', 'Live operating parameters running in this intelligence workspace.'],
}

export default function Layout({ user, onLogout, currentPath, children }) {
  const navigate = useNavigate()
  const meta = META[currentPath] || META['/']
  const [pendingDups, setPendingDups] = useState(0)

  useEffect(() => {
    getDuplicateCount().then(setPendingDups).catch(() => {})
  }, [currentPath])

  const switchRole = async (newRoleUsername) => {
    try {
      await switchUserRole(newRoleUsername)
    } catch (err) {
      console.error('Failed to switch role', err)
    }
  }

  return (
    <div className="app">
      <aside className="side">
        <div className="brand">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>novu</span>
            <span style={{ color: '#38bdf8' }}>.</span>
            <span className="live-pulse" title="System Live"></span>
          </div>
          <small>Opportunity Radar</small>
        </div>

        <nav className="nav" aria-label="Application navigation">
          {NAV.map((item) => (
            <button
              key={item.path}
              data-page={item.path}
              aria-current={currentPath === item.path ? 'page' : undefined}
              onClick={() => navigate(item.path)}
            >
              <span style={{ marginRight: 8, fontSize: 13 }}>{item.icon}</span>
              {item.label}
              {item.path === '/duplicates' && pendingDups > 0 && (
                <span className="nav-badge">{pendingDups}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="side-foot">
          <div className="user-profile-card">
            <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: 13 }}>
              {user?.display_name || user?.username || 'Administrator'}
            </div>
            <span className="role-tag">{user?.role || 'admin'}</span>

            {/* Quick Role Switcher */}
            <div style={{ marginTop: 12 }}>
              <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Switch Active Role:
              </label>
              <select
                className="role-selector"
                value={user?.username || 'admin'}
                onChange={(e) => switchRole(e.target.value)}
              >
                <option value="admin">Administrator</option>
                <option value="manager">Sales Manager</option>
                <option value="executive">Sales Executive A</option>
                <option value="executive_b">Sales Executive B</option>
              </select>
            </div>

            <button
              className="secondary sign-out-btn"
              onClick={onLogout}
            >
              Sign out
            </button>
          </div>
          <div className="workspace-meta">
            Novu Labs Intelligence Desk<br />
            Standalone Autonomous Mode
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="top">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="crumb">NOVU LABS / SALES INTELLIGENCE</span>
            <span className="mode-tag">⚡ Autonomous Radar Mode</span>
          </div>
          <span className="tag">Release v1.0 · Sep 2026</span>
        </header>

        <div className="intro">
          <div>
            <h1>{meta[0]}</h1>
            <p className="sub">{meta[1]}</p>
          </div>
        </div>

        <div className="banner">
          ✓ Autonomous Client Engine Active · Evidence Verification &amp; Deterministic 100-Point Scoring Online
        </div>

        {children}
      </main>
    </div>
  )
}
