"""
Optional team alert email when a client replies to a proposal (only if
TEAM_ALERT_EMAILS is set). Nothing is emailed when a proposal is generated or sent.

Sending runs in a background thread so nobody waits for the mail server, and a
mail problem never breaks the action that triggered it.
"""
import logging
import threading

from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)

# Marks our own alert emails so the reply-inbox watcher never mistakes them for client replies.
ALERT_HEADER = 'X-NovuRadar-Alert'


def is_configured():
    """True when real emails are sent (otherwise they are only printed to the terminal)."""
    return settings.EMAIL_BACKEND.endswith('smtp.EmailBackend')


def lead_url(opportunity):
    return f'{settings.APP_BASE_URL}/lead/{opportunity.id}' if opportunity is not None else settings.APP_BASE_URL


def _send(subject, body, recipients):
    try:
        EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, recipients,
                     headers={ALERT_HEADER: '1'}).send(fail_silently=False)
    except Exception:
        logger.exception('Could not send team alert email: %s', subject)


def send_team_email(subject, body, background=True):
    recipients = settings.TEAM_ALERT_EMAILS
    if not recipients:
        return
    subject = subject.replace('\n', ' ')[:200]
    # Tests use the in-memory backend: send inline so the outbox can be checked.
    if background and not settings.EMAIL_BACKEND.endswith('locmem.EmailBackend'):
        threading.Thread(target=_send, args=(subject, body, recipients), daemon=True).start()
    else:
        _send(subject, body, recipients)


def build_client_reply_email(opportunity, subject, sender, snippet):
    title = opportunity.requirement[:120] if opportunity is not None else (subject or 'a proposal')
    rows = [
        ('Project', opportunity.requirement if opportunity is not None else ''),
        ('From', sender),
        ('Subject', subject),
        ('Project link', opportunity.source_url if opportunity is not None else ''),
        ('Open in NovuRadar', lead_url(opportunity) if opportunity is not None else f'{settings.APP_BASE_URL}/notifications'),
    ]
    lines = [f'{label}: {value}' for label, value in rows if value]
    if snippet:
        lines += ['', 'Message:', snippet.strip()]
    return f'Client replied: {title}', '\n'.join(lines)


def notify_client_reply(opportunity, subject, sender, snippet, background=True):
    send_team_email(*build_client_reply_email(opportunity, subject, sender, snippet), background=background)
