"""
Outbox delivery worker — polls OutboxEvent and delivers via email (SMTP).
Scheduled via Celery beat every 5 minutes.
"""
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def deliver_pending_events(batch_size=50):
    """
    Process up to batch_size pending OutboxEvents.
    Called by Celery beat task.
    """
    from .models import OutboxEvent

    events = OutboxEvent.objects.filter(state='pending').order_by('created_at')[:batch_size]
    delivered = 0
    failed = 0

    for event in events:
        event.state = 'processing'
        event.save(update_fields=['state'])
        try:
            if event.destination == 'email':
                _deliver_email(event)
            elif event.destination == 'csv':
                # CSV is pulled on demand by the export endpoint; the event
                # exists as an audit record that the revision was exportable.
                logger.debug('CSV snapshot event %s acknowledged', event.event_key)
            else:
                logger.info('Unhandled destination %s — acknowledging', event.destination)
        except Exception as exc:
            logger.exception('Delivery failed for event %s: %s', event.id, exc)
            event.state = 'failed'
            event.error = str(exc)[:500]
            failed += 1
        else:
            event.state = 'completed'
            delivered += 1
        event.processed_at = timezone.now()
        event.save(update_fields=['state', 'error', 'processed_at'])

    logger.info('Delivery batch done: %d delivered, %d failed', delivered, failed)
    return delivered, failed


def _deliver_email(event):
    payload = event.payload
    from apps.core.operating_settings import get_setting
    recipient = payload.get('to') or get_setting('alert_email')
    if not recipient:
        logger.warning('Email event %s has no recipient — skipping', event.id)
        event.state = 'completed'
        return
    subject = payload.get('subject', 'Novu Opportunity Radar alert')
    body = payload.get('body', str(payload))
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=False,
    )


try:
    from celery import shared_task

    @shared_task
    def deliver_outbox():
        return deliver_pending_events()

except ImportError:
    pass  # Celery not available in test/dev without broker

