import { useEffect, useRef, useState } from 'react';
import apiClient from '../api/apiClient';
import './ProposalStudio.css';

interface QualityCheck {
  name: string;
  points: number;
  max: number;
  ok: boolean;
  tip: string;
}

interface Quality {
  score: number;
  words: number;
  checks: QualityCheck[];
}

interface Props {
  opportunityId: string;
  sourceUrl?: string;
  /** Called with the updated lead after it is marked as proposal sent. */
  onApplied?: (opportunity: unknown) => void;
}

const TONES = [
  { value: 'professional', label: 'Professional' },
  { value: 'friendly', label: 'Friendly' },
  { value: 'confident', label: 'Confident' },
  { value: 'concise', label: 'Concise' },
];

const LENGTHS = [
  { value: 'short', label: 'Short (~180 words)' },
  { value: 'medium', label: 'Medium (~300 words)' },
  { value: 'long', label: 'Long (~450 words)' },
];

function qualityClass(score: number) {
  if (score >= 75) return 'good';
  if (score >= 50) return 'ok';
  return 'low';
}

export default function ProposalStudio({ opportunityId, sourceUrl, onApplied }: Props) {
  const [tone, setTone] = useState('professional');
  const [length, setLength] = useState('medium');
  const [instructions, setInstructions] = useState('');
  const [includeContact, setIncludeContact] = useState(true);
  const [notice, setNotice] = useState('');
  const [content, setContent] = useState('');
  const [quality, setQuality] = useState<Quality | null>(null);
  const [warning, setWarning] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState<'' | 'generate' | 'save'>('');
  const scoreTimer = useRef<number | undefined>(undefined);

  // Show the last proposal written for this lead, if any.
  useEffect(() => {
    apiClient
      .get(`/opportunities/${opportunityId}/proposal/latest/`)
      .then((res) => {
        if (res.data.content) {
          setContent(res.data.content);
          setQuality(res.data.quality);
          if (res.data.length) setLength(res.data.length);
        }
      })
      .catch(() => undefined);
  }, [opportunityId]);

  // Re-score while the proposal is being edited (debounced).
  function handleEdit(value: string) {
    setContent(value);
    setMessage('');
    window.clearTimeout(scoreTimer.current);
    scoreTimer.current = window.setTimeout(() => {
      apiClient
        .post(`/opportunities/${opportunityId}/proposal/score/`, { content: value, length })
        .then((res) => setQuality(res.data))
        .catch(() => undefined);
    }, 600);
  }

  async function generate() {
    setBusy('generate');
    setError('');
    setMessage('');
    setWarning('');
    setNotice('');
    try {
      const res = await apiClient.post(`/opportunities/${opportunityId}/proposal/`, {
        tone,
        length,
        instructions,
        include_contact: includeContact,
      });
      setContent(res.data.content);
      setQuality(res.data.quality);
      setWarning(res.data.warning || '');
      setNotice(res.data.notice || '');
    } catch {
      setError('Could not generate the proposal. Please try again.');
    } finally {
      setBusy('');
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(content);
      setMessage('Copied — paste it into the bid box.');
    } catch {
      setMessage('Could not copy. Select the text and copy it manually.');
    }
  }

  async function openAndMarkSent() {
    if (!content.trim()) return;
    // Open the project first (inside the click) so the browser does not block the tab.
    if (sourceUrl) window.open(sourceUrl, '_blank', 'noopener,noreferrer');
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      // copying is a convenience; the proposal is still saved below
    }
    setBusy('save');
    setError('');
    try {
      const res = await apiClient.post(`/opportunities/${opportunityId}/proposal/save/`, {
        content,
        tone,
        length,
        applied: true,
      });
      setQuality(res.data.quality);
      setMessage(
        'Proposal copied and saved. The lead is now marked as "proposal" sent, and a copy is emailed to info@novulabs.net.',
      );
      onApplied?.(res.data.opportunity);
    } catch {
      setError('The project was opened, but the proposal could not be saved.');
    } finally {
      setBusy('');
    }
  }

  return (
    <div className="proposal-studio">
      <div className="proposal-controls">
        <label>
          <span>Tone</span>
          <select value={tone} onChange={(e) => setTone(e.target.value)}>
            {TONES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Length</span>
          <select value={length} onChange={(e) => setLength(e.target.value)}>
            {LENGTHS.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
        <label className="proposal-check">
          <input
            type="checkbox"
            checked={includeContact}
            onChange={(e) => setIncludeContact(e.target.checked)}
          />
          <span>Add contact details (info@novulabs.net, +92 326 8292154)</span>
        </label>
        <button type="button" className="proposal-generate" onClick={generate} disabled={busy !== ''}>
          {busy === 'generate' ? 'Writing…' : content ? 'Regenerate' : 'Generate proposal'}
        </button>
      </div>
      <input
        className="proposal-instructions"
        type="text"
        maxLength={500}
        value={instructions}
        placeholder="Optional: anything to mention, e.g. we built a similar food delivery app"
        onChange={(e) => setInstructions(e.target.value)}
      />

      {warning && <p className="proposal-warning">{warning}</p>}
      {notice && <p className="proposal-notice">{notice}</p>}
      {error && <p className="proposal-error">{error}</p>}

      <textarea
        className="proposal-text"
        value={content}
        placeholder="Your AI-written proposal will appear here — edit it freely before sending."
        onChange={(e) => handleEdit(e.target.value)}
        rows={20}
      />

      {quality && content && (
        <div className="proposal-quality">
          <span className={`proposal-score ${qualityClass(quality.score)}`}>Quality {quality.score}/100</span>
          <span className="proposal-words">{quality.words} words</span>
          <ul>
            {quality.checks.map((c) => (
              <li key={c.name} className={c.ok ? 'ok' : 'todo'}>
                {c.ok ? '✓' : '•'} {c.name} ({c.points}/{c.max}){c.tip ? ` — ${c.tip}` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="proposal-actions">
        <button type="button" onClick={copy} disabled={!content.trim()}>
          Copy
        </button>
        {sourceUrl && (
          <button
            type="button"
            className="proposal-primary"
            onClick={openAndMarkSent}
            disabled={!content.trim() || busy !== ''}
          >
            {busy === 'save' ? 'Saving…' : 'Copy, open project & mark sent'}
          </button>
        )}
      </div>
      {message && <p className="proposal-message">{message}</p>}
    </div>
  );
}
