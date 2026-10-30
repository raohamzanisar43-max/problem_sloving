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

function getHealth(source: Source) {
  if (source.last_error) return { label: 'Error', colorVar: '--color-danger' };
  if (!source.enabled) return { label: 'Not enabled', colorVar: '--color-hot' };
  return { label: 'Working', colorVar: '--color-primary' };
}

export default function SourceHealthPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);

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
                {item.last_error && <p className="source-error">{item.last_error}</p>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}