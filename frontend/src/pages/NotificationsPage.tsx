import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';
import PageHeader from '../components/PageHeader';
import { formatPosted } from '../utils/posted';
import { NOTIFICATIONS_CHANGED, announceNotificationsChanged as announceChange } from '../utils/notifications';
import './NotificationsPage.css';

interface NotificationItem {
  id: string;
  kind: string;
  title: string;
  body: string;
  sender: string;
  opportunity: string | null;
  opportunity_title: string;
  read: boolean;
  created_at: string;
}

interface InboxStatus {
  configured: boolean;
  mailbox: string;
  last_check: string | null;
  last_ok: boolean | null;
  last_error: string;
}

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [inbox, setInbox] = useState<InboxStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState('');
  const [desktop, setDesktop] = useState(
    typeof Notification !== 'undefined' ? Notification.permission : 'denied',
  );
  const navigate = useNavigate();

  const load = useCallback(() => {
    Promise.all([apiClient.get('/notifications/'), apiClient.get('/notifications/inbox-status/')])
      .then(([list, status]) => {
        setItems(list.data);
        setInbox(status.data);
      })
      .catch(() => setMessage('Could not load notifications.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    window.addEventListener(NOTIFICATIONS_CHANGED, load);
    return () => window.removeEventListener(NOTIFICATIONS_CHANGED, load);
  }, [load]);

  async function open(item: NotificationItem) {
    if (!item.read) {
      await apiClient.post(`/notifications/${item.id}/read/`).catch(() => undefined);
      announceChange();
    }
    if (item.opportunity) navigate(`/lead/${item.opportunity}`);
  }

  async function markAllRead() {
    await apiClient.post('/notifications/read-all/').catch(() => undefined);
    announceChange();
  }

  async function checkNow() {
    setChecking(true);
    setMessage('');
    try {
      const res = await apiClient.post('/notifications/check-inbox/');
      const result = res.data.result;
      setMessage(
        result?.ok
          ? `Checked ${result.scanned} email(s): ${result.notified} new reply notification(s).`
          : `Inbox check failed: ${result?.error ?? 'unknown error'}`,
      );
      announceChange();
    } catch {
      setMessage('The inbox check failed.');
    } finally {
      setChecking(false);
    }
  }

  async function enableDesktop() {
    if (typeof Notification === 'undefined') return;
    setDesktop(await Notification.requestPermission());
  }

  const unread = items.filter((i) => !i.read).length;

  return (
    <div className="notif-page">
      <PageHeader title="Notifications" />
      <div className="notif-content">
        {inbox && !inbox.configured && (
          <div className="notif-banner warn">
            <strong>The reply inbox is not connected yet.</strong> Client replies are read from the company
            mailbox (info@novulabs.net). Add <code>INBOX_IMAP_HOST</code>, <code>INBOX_EMAIL</code> and{' '}
            <code>INBOX_PASSWORD</code> to the backend <code>.env</code> and restart — then every reply to a
            proposal shows up here.
          </div>
        )}
        {inbox?.configured && (
          <div className={`notif-banner ${inbox.last_ok === false ? 'warn' : 'ok'}`}>
            Watching <strong>{inbox.mailbox}</strong> for client replies.
            {inbox.last_check && ` Last checked ${new Date(inbox.last_check).toLocaleString()}.`}
            {inbox.last_ok === false && inbox.last_error && <div>Problem: {inbox.last_error}</div>}
          </div>
        )}

        <div className="notif-toolbar">
          <span className="notif-count">{unread} unread</span>
          <button type="button" onClick={markAllRead} disabled={unread === 0}>
            Mark all as read
          </button>
          {inbox?.configured && (
            <button type="button" onClick={checkNow} disabled={checking}>
              {checking ? 'Checking…' : 'Check inbox now'}
            </button>
          )}
          {desktop === 'default' && (
            <button type="button" onClick={enableDesktop}>
              Enable desktop alerts
            </button>
          )}
        </div>
        {message && <p className="notif-message">{message}</p>}

        {loading ? (
          <p className="notif-empty">Loading…</p>
        ) : items.length === 0 ? (
          <p className="notif-empty">
            No notifications yet. When a client replies to one of your proposals, it will appear here.
          </p>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              className={`notif-card${item.read ? '' : ' unread'}${item.opportunity ? ' clickable' : ''}`}
              onClick={() => open(item)}
            >
              <div className="notif-card-head">
                <span className="notif-kind">
                  {item.kind === 'marketplace_message' ? 'Marketplace message' : 'Client reply'}
                </span>
                <span className="notif-time">
                  {formatPosted(item.created_at)} · {new Date(item.created_at).toLocaleTimeString()}
                </span>
              </div>
              <p className="notif-title">{item.title}</p>
              {item.sender && <p className="notif-sender">From: {item.sender}</p>}
              <p className="notif-body">{item.body}</p>
              {item.opportunity && <span className="notif-link">Open lead →</span>}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
