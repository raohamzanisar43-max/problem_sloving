import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';
import { logout } from '../api/authService';
import PageHeader from '../components/PageHeader';
import './SettingsPage.css';

interface Me {
  username: string;
  role: string;
  email: string;
  can_manage_keywords?: boolean;
}

interface SearchTerm {
  id: string;
  query: string;
  group_name: string;
  enabled: boolean;
}

interface Paginated<T> {
  results: T[];
  next: string | null;
}

/** Turn a DRF error response into one readable line. */
function errorText(err: unknown, fallback: string): string {
  const data = (err as { response?: { data?: unknown } })?.response?.data;
  if (data && typeof data === 'object') {
    const values = Object.values(data as Record<string, unknown>).flat();
    const first = values.find((v) => typeof v === 'string');
    if (typeof first === 'string') return first;
  }
  return fallback;
}

/**
 * Keywords the web-search collector actually runs. New keywords are attached
 * to that source by the API, so the list here is exactly what gets searched.
 */
async function fetchAllSearchTerms(): Promise<SearchTerm[]> {
  const sources: { data: Paginated<{ id: string; connector_type: string }> } = await apiClient.get(
    '/sources/?page_size=100'
  );
  const web = sources.data.results.find((s) => s.connector_type === 'web_search');
  const all: SearchTerm[] = [];
  let url: string | null = `/search-terms/?all=1&page_size=100${web ? `&source=${web.id}` : ''}`;
  while (url) {
    const res: { data: Paginated<SearchTerm> } = await apiClient.get(url);
    all.push(...res.data.results);
    url = res.data.next;
  }
  return all;
}

export default function SettingsPage() {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // Search keywords
  const [terms, setTerms] = useState<SearchTerm[]>([]);
  const [newTerm, setNewTerm] = useState('');
  const [termError, setTermError] = useState('');
  const [termBusy, setTermBusy] = useState(false);

  // Ignore words (edited locally, saved with one button)
  const [ignoreWords, setIgnoreWords] = useState<string[]>([]);
  const [savedIgnoreWords, setSavedIgnoreWords] = useState<string[]>([]);
  const [newIgnore, setNewIgnore] = useState('');
  const [ignoreMessage, setIgnoreMessage] = useState('');
  const [ignoreError, setIgnoreError] = useState('');
  const [ignoreBusy, setIgnoreBusy] = useState(false);

  const canManage = Boolean(user?.can_manage_keywords);
  const ignoreDirty = ignoreWords.join('\n') !== savedIgnoreWords.join('\n');
  const activeCount = terms.filter((t) => t.enabled).length;

  useEffect(() => {
    Promise.all([
      apiClient.get('/me/').then((res) => setUser(res.data)),
      fetchAllSearchTerms().then(setTerms),
      apiClient.get('/ignore-keywords/').then((res) => {
        setIgnoreWords(res.data.keywords ?? []);
        setSavedIgnoreWords(res.data.keywords ?? []);
      }),
    ])
      .catch((err) => console.log('Error loading settings:', err))
      .finally(() => setLoading(false));
  }, []);

  function handleLogout() {
    if (window.confirm('Are you sure you want to log out?')) {
      logout();
      navigate('/login');
    }
  }

  async function addTerm(e: FormEvent) {
    e.preventDefault();
    const query = newTerm.trim();
    if (!query) return;
    setTermBusy(true);
    setTermError('');
    try {
      const res = await apiClient.post('/search-terms/', { query });
      setTerms((prev) => [...prev, res.data]);
      setNewTerm('');
    } catch (err) {
      setTermError(errorText(err, 'Could not add the keyword.'));
    } finally {
      setTermBusy(false);
    }
  }

  async function toggleTerm(term: SearchTerm) {
    setTermError('');
    try {
      const res = await apiClient.patch(`/search-terms/${term.id}/`, { enabled: !term.enabled });
      setTerms((prev) => prev.map((t) => (t.id === term.id ? res.data : t)));
    } catch (err) {
      setTermError(errorText(err, 'Could not update the keyword.'));
    }
  }

  async function deleteTerm(term: SearchTerm) {
    if (!window.confirm(`Delete the keyword "${term.query}"?`)) return;
    setTermError('');
    try {
      await apiClient.delete(`/search-terms/${term.id}/`);
      setTerms((prev) => prev.filter((t) => t.id !== term.id));
    } catch (err) {
      setTermError(errorText(err, 'Could not delete the keyword.'));
    }
  }

  function addIgnoreWord(e: FormEvent) {
    e.preventDefault();
    // Commas separate words, so "guide, tips" adds two.
    const words = newIgnore
      .split(',')
      .map((w) => w.trim().toLowerCase().replace(/\s+/g, ' '))
      .filter(Boolean);
    if (!words.length) return;
    setIgnoreWords((prev) => [...prev, ...words.filter((w) => !prev.includes(w))]);
    setNewIgnore('');
    setIgnoreMessage('');
  }

  function removeIgnoreWord(word: string) {
    setIgnoreWords((prev) => prev.filter((w) => w !== word));
    setIgnoreMessage('');
  }

  async function saveIgnoreWords() {
    setIgnoreBusy(true);
    setIgnoreError('');
    setIgnoreMessage('');
    try {
      const res = await apiClient.put('/ignore-keywords/', { keywords: ignoreWords });
      setIgnoreWords(res.data.keywords);
      setSavedIgnoreWords(res.data.keywords);
      setIgnoreMessage(
        `Saved and applied. ${res.data.rejected} lead(s) hidden, ${res.data.restored} lead(s) brought back.`
      );
    } catch (err) {
      setIgnoreError(errorText(err, 'Could not save the ignore words.'));
    } finally {
      setIgnoreBusy(false);
    }
  }

  // Group keywords by their group name for display.
  const groups = terms.reduce<Record<string, SearchTerm[]>>((acc, t) => {
    (acc[t.group_name || 'Other'] ||= []).push(t);
    return acc;
  }, {});

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

          {/* ── Search keywords ── */}
          <p className="settings-section-label">Search keywords</p>
          <p className="settings-help">
            Posts are searched with these keywords on every scheduled run — write them the way a client
            would post a job, e.g. <em>need someone to build my website</em>. Each keyword that is ON
            uses 1 search call per run ({activeCount} ON now).
          </p>
          <div className="settings-card">
            {canManage && (
              <form className="settings-add-row" onSubmit={addTerm}>
                <input
                  type="text"
                  value={newTerm}
                  maxLength={200}
                  placeholder="e.g. need a developer to build my app"
                  onChange={(e) => setNewTerm(e.target.value)}
                />
                <button type="submit" className="settings-primary-button" disabled={termBusy || !newTerm.trim()}>
                  Add
                </button>
              </form>
            )}
            {termError && <p className="settings-error">{termError}</p>}
            {terms.length === 0 ? (
              <p className="settings-empty">No keywords yet.</p>
            ) : (
              Object.entries(groups).map(([group, items]) => (
                <div key={group}>
                  <p className="settings-group-label">{group}</p>
                  {items.map((term) => (
                    <div key={term.id} className={`settings-term-row${term.enabled ? '' : ' is-off'}`}>
                      <span className="settings-term-text">{term.query}</span>
                      {canManage ? (
                        <span className="settings-term-actions">
                          <label className="settings-switch" title={term.enabled ? 'Switch off' : 'Switch on'}>
                            <input type="checkbox" checked={term.enabled} onChange={() => toggleTerm(term)} />
                            <span>{term.enabled ? 'ON' : 'OFF'}</span>
                          </label>
                          <button
                            type="button"
                            className="settings-delete-button"
                            onClick={() => deleteTerm(term)}
                            aria-label={`Delete ${term.query}`}
                          >
                            Delete
                          </button>
                        </span>
                      ) : (
                        <span className="settings-row-label">{term.enabled ? 'ON' : 'OFF'}</span>
                      )}
                    </div>
                  ))}
                </div>
              ))
            )}
          </div>

          {/* ── Ignore words ── */}
          <p className="settings-section-label">Ignore words</p>
          <p className="settings-help">
            A post whose title, text or link contains any of these words is never shown — use this for
            irrelevant results such as <em>guide</em>, <em>top 10</em> or <em>development company</em>.
            Saving also re-checks the leads already in the queue.
          </p>
          <div className="settings-card">
            {canManage && (
              <form className="settings-add-row" onSubmit={addIgnoreWord}>
                <input
                  type="text"
                  value={newIgnore}
                  maxLength={300}
                  placeholder="e.g. tutorial, best companies"
                  onChange={(e) => setNewIgnore(e.target.value)}
                />
                <button type="submit" className="settings-secondary-button" disabled={!newIgnore.trim()}>
                  Add
                </button>
              </form>
            )}
            <div className="settings-chips">
              {ignoreWords.length === 0 && <p className="settings-empty">No ignore words.</p>}
              {ignoreWords.map((word) => (
                <span key={word} className="settings-chip">
                  {word}
                  {canManage && (
                    <button type="button" onClick={() => removeIgnoreWord(word)} aria-label={`Remove ${word}`}>
                      ×
                    </button>
                  )}
                </span>
              ))}
            </div>
            {canManage && (
              <div className="settings-save-row">
                {ignoreDirty && <span className="settings-unsaved">Unsaved changes</span>}
                <button
                  type="button"
                  className="settings-primary-button"
                  onClick={saveIgnoreWords}
                  disabled={ignoreBusy || !ignoreDirty}
                >
                  {ignoreBusy ? 'Applying...' : 'Save & apply'}
                </button>
              </div>
            )}
            {ignoreError && <p className="settings-error">{ignoreError}</p>}
            {ignoreMessage && <p className="settings-success">{ignoreMessage}</p>}
          </div>

          {!canManage && (
            <p className="settings-help">Only an admin or sales manager can change keywords.</p>
          )}

          <button className="logout-button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      )}
    </div>
  );
}
