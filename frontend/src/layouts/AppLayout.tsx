import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { logout } from '../api/authService';
import './AppLayout.css';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/opportunities', label: 'Opportunities' },
  { to: '/pipeline', label: 'Sales Pipeline' },
  { to: '/review', label: 'Review Queue' },
  { to: '/source-health', label: 'Source Health' },
  { to: '/settings', label: 'Settings' },
];

export default function AppLayout() {
  const navigate = useNavigate();

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