import { useEffect, useState, useCallback } from 'react';
import apiClient from '../api/apiClient';
import PageHeader from '../components/PageHeader';
import './SourceHealthPage.css';

interface Source {
  id: string;
  name: string;
  connector_type: string;
  enabled: boolean;
  planned_route: string;
  last_success_at: string | null;
  last_error: string;
}

// Sources the scheduler can collect from (the rest are placeholders or manual).
const COLLECTABLE = ['freelancer', 'reddit', 'web_search', 'rss', 'rfp_portal', 'x'];

function getHealth(source: Source) {
  if (!source.enabled) return { label: 'Switched off', colorVar: '--color-hot' };
  if (source.last_error) return { label: 'Error', colorVar: '--color-danger' };
  return { label: 'Working', colorVar: '--color-primary' };
}

export default function SourceHealthPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [messages, setMessages] = useState<Record<string, string>>({});

  function say(id: string, text: string) {
    setMessages((m) => ({ ...m, [id]: text }));
  }

  async function toggle(item: Source) {
    setBusy(item.id);
    try {
      await apiClient.patch(`/sources/${item.id}/`, { enabled: !item.enabled });
      say(item.id, item.enabled ? 'Switched off — no new leads from this source.' : 'Switched on.');
      loadSources();
    } catch {
      say(item.id, 'Only an admin can switch sources on or off.');
    } finally {
      setBusy('');
    }
  }

  async function runNow(item: Source) {
    setBusy(item.id);
    try {
      const res = await apiClient.post(`/sources/${item.id}/run-now/`);
      say(item.id, res.data.detail);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      say(item.id, detail ?? 'Could not start the run.');
    } finally {
      setBusy('');
    }
  }

  const loadSources = useCallback(() => {
    apiClient
      .get('/sources/')
      .then((res) => setSources(res.data.results ?? res.data))
      .catch((err) => console.log('Error loading sources:', err))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadSources();
  }, [loadSources]);

  return (
    <div className="source-health-page">
      <PageHeader title="Source Health" />
      {loading ? (
        <div className="source-health-loading">Loading...</div>
      ) : (
        <div className="source-health-content">
          {sources.map((item) => {
            const health = getHealth(item);
            return (
              <div key={item.id} className="source-card">
                <div className="source-card-row">
                  <span className="source-name">{item.name}</span>
                  <div className="source-status-row">
                    <span className="source-status-dot" style={{ background: `var(${health.colorVar})` }} />
                    <span className="source-status-text" style={{ color: `var(${health.colorVar})` }}>
                      {health.label}
                    </span>
                  </div>
                </div>
                <p className="source-meta">
                  {item.connector_type.toUpperCase()} · {item.planned_route}
                </p>
                <p className="source-meta">
                  {item.last_success_at
                    ? `Last successful run: ${new Date(item.last_success_at).toLocaleString()}`
                    : 'Never run yet'}
                </p>
                {item.enabled && item.last_error && <p className="source-error">{item.last_error}</p>}
                {COLLECTABLE.includes(item.connector_type) && (
                  <div className="source-actions">
                    <button type="button" onClick={() => toggle(item)} disabled={busy === item.id}>
                      {item.enabled ? 'Switch off' : 'Switch on'}
                    </button>
                    {item.enabled && (
                      <button type="button" className="primary" onClick={() => runNow(item)} disabled={busy === item.id}>
                        Run now
                      </button>
                    )}
                  </div>
                )}
                {messages[item.id] && <p className="source-message">{messages[item.id]}</p>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}