"""
Reply inbox watcher.

Proposals end with the company email (info@novulabs.net), and marketplaces such
as Freelancer.com email an alert when a client messages or awards you. This
module reads that mailbox over IMAP (read-only — messages stay unread in the
mail client), matches each new email to the lead it answers, and creates an
in-app notification plus an activity on the lead.

Configure with INBOX_IMAP_HOST / INBOX_EMAIL / INBOX_PASSWORD in .env; when they
are missing the watcher does nothing.
"""
import email
import imaplib
import logging
import re
from datetime import timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from html import unescape

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.opportunities.models import Activity, Opportunity
from apps.scoring.capability_profile import CAPABILITY_PROFILE
from .mailer import ALERT_HEADER, notify_client_reply
from .models import InboxCheck, InboxMessage, Notification

logger = logging.getLogger(__name__)

# Leads someone has applied to / is talking to — the ones a reply can belong to.
REPLY_STATUSES = ('proposal', 'contacted', 'meeting', 'reviewed', 'won')
MARKETPLACE_DOMAINS = ('freelancer.com', 'upwork.com', 'fiverr.com', 'peopleperhour.com', 'guru.com')
# Marketplace alerts worth a notification even when no lead matches.
MARKETPLACE_ALERT_RE = re.compile(
    r'message|messaged|sent you|replied|reply|award|awarded|hire|hired|milestone|chat|invite|interview|offer',
    re.IGNORECASE,
)
# Automated mail that is never a client reply.
IGNORE_SENDER_RE = re.compile(r'no-?reply@|mailer-daemon|postmaster@', re.IGNORECASE)
STAFF_ROLES = ('admin', 'sales_manager', 'sales_executive')
MAX_MESSAGES = 200


def inbox_settings():
    return settings.INBOX


def is_configured():
    cfg = inbox_settings()
    return bool(cfg.get('HOST') and cfg.get('USER') and cfg.get('PASSWORD'))


def _decode(value):
    if not value:
        return ''
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return str(value)


def message_text(msg):
    """Plain text of an email (text/plain preferred, HTML stripped otherwise)."""
    plain, html = [], []
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition', '').startswith('attachment'):
            continue
        try:
            payload = part.get_payload(decode=True) or b''
            text = payload.decode(part.get_content_charset() or 'utf-8', errors='replace')
        except Exception:
            continue
        if part.get_content_type() == 'text/plain':
            plain.append(text)
        elif part.get_content_type() == 'text/html':
            html.append(text)
    if plain:
        return '\n'.join(plain)
    text = '\n'.join(html)
    text = re.sub(r'(?is)<(script|style).*?</\1>', ' ', text)
    text = re.sub(r'(?i)<br\s*/?>|</p>|</div>|</tr>', '\n', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    return unescape(re.sub(r'[ \t]+', ' ', text))


def _norm(text):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', (text or '').lower())).strip()


def _url_slug(url):
    """Last path segment of a project URL, e.g. 'build-flutter-food-app'."""
    path = re.sub(r'[?#].*$', '', url or '').rstrip('/')
    slug = path.rsplit('/', 1)[-1] if '/' in path else ''
    return slug.lower() if len(slug) >= 8 else ''


def candidate_leads():
    since = timezone.now() - timedelta(days=120)
    return Opportunity.objects.filter(status__in=REPLY_STATUSES, updated_at__gte=since).select_related('owner')


def match_opportunity(subject, body, sender_email, leads=None):
    """The lead an email answers: by sender address, project link or project title."""
    leads = list(candidate_leads() if leads is None else leads)
    haystack_raw = f'{subject}\n{body}'.lower()
    haystack = _norm(haystack_raw)
    sender_email = (sender_email or '').lower()

    for lead in leads:
        if lead.email and sender_email and lead.email.lower() == sender_email:
            return lead
    for lead in leads:
        slug = _url_slug(lead.source_url)
        if slug and slug in haystack_raw:
            return lead
    best, best_len = None, 0
    for lead in leads:
        title = _norm(lead.requirement)
        if len(title) >= 12 and title in haystack and len(title) > best_len:
            best, best_len = lead, len(title)
    return best


def _is_marketplace(sender_email):
    domain = sender_email.rsplit('@', 1)[-1].lower() if '@' in sender_email else ''
    return any(domain == d or domain.endswith('.' + d) for d in MARKETPLACE_DOMAINS)


def _looks_like_reply_to_us(subject, body):
    """A reply to an email that carried our proposal/signature."""
    contact = CAPABILITY_PROFILE['contact']['email'].lower()
    return bool(re.match(r'^\s*(re|aw|sv)\s*:', subject, re.IGNORECASE)) and (
        contact in body.lower() or 'novulabs' in body.lower()
    )


def recipients_for(opportunity):
    User = get_user_model()
    if opportunity is not None and opportunity.owner_id and opportunity.owner.is_active:
        return [opportunity.owner]
    return list(User.objects.filter(is_active=True, role__in=STAFF_ROLES))


def _snippet(body, limit=600):
    # Drop quoted history ("> ..." and "On <date>, X wrote:") so the new text shows first.
    lines = []
    for line in body.splitlines():
        if line.strip().startswith('>') or re.match(r'^\s*On .{5,120} wrote:\s*$', line):
            break
        lines.append(line)
    text = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()
    return text[:limit]


def process_message(msg, own_address=''):
    """
    Handle one parsed email. Returns the notifications created (may be empty).
    Safe to call twice for the same email — it is recorded by Message-ID.
    """
    message_id = (msg.get('Message-ID') or '').strip()[:255]
    subject = _decode(msg.get('Subject'))[:255]
    sender_name, sender_email = parseaddr(_decode(msg.get('From')))
    sender_email = sender_email.lower()
    if not message_id:
        message_id = f'no-id:{sender_email}:{subject}:{msg.get("Date", "")}'[:255]
    if InboxMessage.objects.filter(message_id=message_id).exists():
        return []
    try:
        received = parsedate_to_datetime(msg.get('Date')) if msg.get('Date') else None
    except (TypeError, ValueError):
        received = None

    record = InboxMessage(message_id=message_id, subject=subject, sender=sender_email, received_at=received)
    marketplace = _is_marketplace(sender_email)
    automated = IGNORE_SENDER_RE.search(sender_email) and not marketplace
    own = {a.lower() for a in (own_address, settings.EMAIL_HOST_USER) if a}
    if sender_email in own or automated or msg.get(ALERT_HEADER):
        record.save()
        return []

    body = message_text(msg)
    lead = match_opportunity(subject, body, sender_email)

    if lead is not None:
        kind = 'marketplace_message' if marketplace else 'client_reply'
        title = f'Reply on: {lead.requirement[:150]}'
    elif marketplace and MARKETPLACE_ALERT_RE.search(subject):
        kind, title = 'marketplace_message', subject or 'New marketplace message'
    elif _looks_like_reply_to_us(subject, body):
        kind, title = 'client_reply', subject
    else:
        record.save()
        return []

    who = sender_name or sender_email
    created = []
    with transaction.atomic():
        record.opportunity = lead
        record.notified = True
        record.save()
        snippet = _snippet(body)
        for user in recipients_for(lead):
            created.append(Notification.objects.create(
                recipient=user, opportunity=lead, kind=kind, title=title[:255],
                body=f'{subject}\n\n{snippet}'.strip(), sender=who[:255], message_id=message_id,
            ))
        if lead is not None:
            Activity.objects.create(
                opportunity=lead, action='client_reply', to_value=who[:255],
                payload={'subject': subject, 'from': sender_email, 'snippet': snippet[:300]},
            )
        # One alert email to the team mailbox, after the records are saved.
        transaction.on_commit(lambda: notify_client_reply(
            lead, subject, f'{who} <{sender_email}>' if sender_name else sender_email, snippet))
    return created


def check_inbox():
    """Read new mail from the configured inbox. Returns a summary dict."""
    if not is_configured():
        return {'configured': False, 'scanned': 0, 'notified': 0}
    cfg = inbox_settings()
    scanned = notified = 0
    try:
        conn = imaplib.IMAP4_SSL(cfg['HOST'], int(cfg.get('PORT') or 993), timeout=60)
        try:
            conn.login(cfg['USER'], cfg['PASSWORD'])
            conn.select(cfg.get('FOLDER') or 'INBOX', readonly=True)
            since = (timezone.now() - timedelta(days=int(cfg.get('LOOKBACK_DAYS') or 3))).strftime('%d-%b-%Y')
            status, data = conn.search(None, 'SINCE', since)
            ids = (data[0].split() if status == 'OK' and data and data[0] else [])[-MAX_MESSAGES:]
            for num in ids:
                status, parts = conn.fetch(num, '(BODY.PEEK[])')
                if status != 'OK' or not parts or not isinstance(parts[0], tuple):
                    continue
                msg = email.message_from_bytes(parts[0][1])
                scanned += 1
                notified += 1 if process_message(msg, own_address=cfg['USER']) else 0
        finally:
            try:
                conn.logout()
            except Exception:
                pass
    except Exception as exc:
        logger.error('Inbox check failed: %s', exc)
        error = str(exc)
        if 'AUTHENTICATIONFAILED' in error.upper() or 'invalid credentials' in error.lower():
            error = ('Login failed — check INBOX_EMAIL / INBOX_PASSWORD. Gmail and Google Workspace need an '
                     'App Password, and IMAP must be enabled for the mailbox.')
        InboxCheck.objects.create(ok=False, error=error[:500], scanned=scanned, notified=notified)
        return {'configured': True, 'ok': False, 'error': error, 'scanned': scanned, 'notified': notified}
    InboxCheck.objects.create(ok=True, scanned=scanned, notified=notified)
    # Keep the history short.
    old = InboxCheck.objects.order_by('-created_at').values_list('id', flat=True)[50:]
    InboxCheck.objects.filter(id__in=list(old)).delete()
    return {'configured': True, 'ok': True, 'scanned': scanned, 'notified': notified}
