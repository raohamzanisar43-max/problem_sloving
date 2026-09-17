import { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { getMe, logout } from './api/client'
import Login from './pages/Login'
import Layout from './components/navbar'
import Overview from './pages/Overview'
import Opportunities from './pages/Opportunities'
import Sources from './pages/Sources'
import Rules from './pages/Rules'
import Pipeline from './pages/Pipeline'
import Exports from './pages/Exports'
import Settings from './pages/Settings'
import LeadDetail from './components/LeadDetail'
import Duplicates from './pages/Duplicates'
import Capture from './pages/Capture'

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedLead, setSelectedLead] = useState(null)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setLoading(false)
      return
    }
    getMe()
      .then(setUser)
      .catch(() => {
        logout()
      })
      .finally(() => setLoading(false))
  }, [])

  const handleLogin = (u) => {
    setUser(u)
    navigate('/')
  }

  const handleLogout = () => {
    logout()
    setUser(null)
    navigate('/login')
  }

  if (loading) {
    return <div className="login-page"><p>Loading…</p></div>
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login onLogin={handleLogin} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <>
      <Layout
        user={user}
        onLogout={handleLogout}
        onSwitchUser={(nextUser) => {
          setUser(nextUser)
          setSelectedLead(null)
          navigate('/')
        }}
        currentPath={location.pathname}
      >
        <Routes>
          <Route path="/" element={<Overview onOpenLead={setSelectedLead} />} />
          <Route path="/opportunities" element={<Opportunities onOpenLead={setSelectedLead} />} />
          <Route path="/capture" element={<Capture onOpenLead={setSelectedLead} />} />
          <Route path="/sources" element={<Sources userRole={user.role} />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/pipeline" element={<Pipeline onOpenLead={setSelectedLead} />} />
          <Route path="/duplicates" element={<Duplicates />} />
          <Route path="/exports" element={<Exports />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
      {selectedLead && (
        <LeadDetail
          leadId={selectedLead}
          onClose={() => setSelectedLead(null)}
          onSaved={() => {}}
        />
      )}
    </>
  )
}
