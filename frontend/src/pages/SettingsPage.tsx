import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';
import { logout } from '../api/authService';
import PageHeader from '../components/PageHeader';
import './SettingsPage.css';

interface Me {
  username: string;
  role: string;
  email: string;
}

export default function SettingsPage() {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    apiClient
      .get('/me/')
      .then((res) => setUser(res.data))
      .catch((err) => console.log('Error loading account:', err))
      .finally(() => setLoading(false));
  }, []);

  function handleLogout() {
    if (window.confirm('Are you sure you want to log out?')) {
      logout();
      navigate('/login');
    }
  }

  return (
    <div className="settings-page">
      <PageHeader title="Settings" />
      {loading ? (
        <div className="settings-loading">Loading...</div>
      ) : (
        <div className="settings-content">
          <p className="settings-section-label">Account</p>
          <div className="settings-card">
            <div className="settings-row">
              <span className="settings-row-label">Username</span>
              <span className="settings-row-value">{user?.username ?? '—'}</span>
            </div>
            <div className="settings-row">
              <span className="settings-row-label">Role</span>
              <span className="settings-row-value">{user?.role ?? '—'}</span>
            </div>
            <div className="settings-row">
              <span className="settings-row-label">Email</span>
              <span className="settings-row-value">{user?.email ?? '—'}</span>
            </div>
          </div>
          <button className="logout-button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      )}
    </div>
  );
}