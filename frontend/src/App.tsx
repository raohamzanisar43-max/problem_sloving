import type { ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import SalesPipelinePage from './pages/SalesPipelinePage';
import LeadDetailPage from './pages/LeadDetailPage';
import SourceHealthPage from './pages/SourceHealthPage';
import SettingsPage from './pages/SettingsPage';
import OpportunityQueuePage from './pages/OpportunityQueuePage';
import ReviewQueuePage from './pages/ReviewQueuePage';
import AppLayout from './layouts/AppLayout';
import { isLoggedIn } from './api/authService';

function RequireAuth({ children }: { children: ReactNode }) {
  return isLoggedIn() ? <>{children}</> : <Navigate to="/login" />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/opportunities" element={<OpportunityQueuePage />} />
          <Route path="/pipeline" element={<SalesPipelinePage />} />
          <Route path="/review" element={<ReviewQueuePage />} />
          <Route path="/source-health" element={<SourceHealthPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/lead/:id" element={<LeadDetailPage />} />
        </Route>
        <Route path="/" element={<Navigate to={isLoggedIn() ? '/dashboard' : '/login'} />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;