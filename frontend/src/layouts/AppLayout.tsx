import { useEffect, useRef, useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';
import { logout } from '../api/authService';
import { NOTIFICATIONS_CHANGED } from '../utils/notifications';
import './AppLayout.css';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/opportunities', label: 'Opportunities' },
  { to: '/notifications', label: 'Notifications' },
  { to: '/pipeline', label: 'Sales Pipeline' },
  { to: '/review', label: 'Review Queue' },
  { to: '/source-health', label: 'Source Health' },
  { to: '/settings', label: 'Settings' },
];

const POLL_MS = 60_000;

interface UnreadSummary {
  count: number;
  latest: { id: string; title: string; body: string; opportunity: string | null } | null;
}

/** Unread notification count, refreshed every minute; shows a desktop alert for new replies. */
function useUnreadNotifications() {
  const [count, setCount] = useState(0);
  const lastSeen = useRef<string | null | undefined>(undefined);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    function poll() {
      apiClient
        .get<UnreadSummary>('/notifications/unread-count/')
        .then((res) => {
          if (cancelled) return;
          setCount(res.data.count);
          const latest = res.data.latest;
          // Skip the very first poll so old notifications don't pop up on every page load.
          if (latest && lastSeen.current !== undefined && latest.id !== lastSeen.current
              && typeof Notification !== 'undefined' && Notification.permission === 'granted') {
            const alert = new Notification(latest.title, { body: latest.body.slice(0, 160) });
            alert.onclick = () => {
              window.focus();
              navigate(latest.opportunity ? `/lead/${latest.opportunity}` : '/notifications');
            };
          }
          lastSeen.current = latest?.id ?? null;
        })
        .catch(() => undefined);
    }
    poll();
    const timer = window.setInterval(poll, POLL_MS);
    window.addEventListener(NOTIFICATIONS_CHANGED, poll);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.removeEventListener(NOTIFICATIONS_CHANGED, poll);
    };
  }, [navigate]);

  return count;
}

export default function AppLayout() {
  const navigate = useNavigate();
  const unread = useUnreadNotifications();

  useEffect(() => {
    const base = document.title.replace(/^\(\d+\)\s*/, '');
    document.title = unread > 0 ? `(${unread}) ${base}` : base;
  }, [unread]);

  function handleLogout() {
    if (window.confirm('Are you sure you want to log out?')) {
      logout();
      navigate('/login');
    }
  }

  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <div className="app-sidebar-brand">
          <div className="app-sidebar-logo">NR</div>
          <div>
            <div className="app-sidebar-title">Novu Opportunity Radar</div>
            <div className="app-sidebar-subtitle">Sales Intelligence</div>
          </div>
        </div>

        <nav className="app-sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `app-sidebar-link${isActive ? ' active' : ''}`}
            >
              {item.label}
              {item.to === '/notifications' && unread > 0 && (
                <span className="app-sidebar-badge">{unread > 99 ? '99+' : unread}</span>
              )}
            </NavLink>
          ))}
        </nav>

        <button className="app-sidebar-logout" onClick={handleLogout}>
          Logout
        </button>
      </aside>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
