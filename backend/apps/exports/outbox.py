"""
Outbox helpers (handover §9, §12).

Every export- or alert-worthy change to an Opportunity is recorded as an
OutboxEvent inside the caller's transaction. The event key is
``destination:opportunity:revision`` so a replay of the same revision is a
no-op rather than a duplicate delivery.
"""
import logging

from apps.core.operating_settings import get_setting

logger = logging.getLogger(__name__)


def emit(destination, opportunity, payload=None, revision=None):
    """
    Record an idempotent outbox event. Returns the OutboxEvent, or None when an
    event for this destination/opportunity/revision already exists.
    """
    from .models import OutboxEvent

    revision = opportunity.revision if revision is None else revision
    event_key = f'{destination}:{opportunity.id}:{revision}'
    event, created = OutboxEvent.objects.get_or_create(
        event_key=event_key,
        defaults={
            'destination': destination,
            'opportunity_id': opportunity.id,
            'revision': revision,
            'payload': payload or {},
        },
    )
    return event if created else None


def opportunity_payload(opportunity):
    """Compact, non-sensitive representation used by outbox consumers."""
    return {
        'opportunity_id': str(opportunity.id),
        'public_id': opportunity.public_id,
        'requirement': opportunity.requirement,
        'company_name': opportunity.company_name,
        'primary_category': opportunity.primary_category,
        'score': opportunity.score,
        'band': opportunity.band,
        'status': opportunity.status,
        'source_url': opportunity.source_url,
        'revision': opportunity.revision,
    }


def emit_for_opportunity(opportunity, reason='changed'):
    """
    Emit the standard fan-out for an opportunity: always a `csv` snapshot
    event, plus an `email` alert when the lead clears the alert threshold.
    """
    payload = opportunity_payload(opportunity)
    payload['reason'] = reason
    emit('csv', opportunity, payload)

    alert_email = get_setting('alert_email')
    min_score = int(get_setting('alert_min_score'))
    if alert_email and opportunity.score >= min_score and opportunity.status not in ('rejected', 'closed'):
        emit('email', opportunity, {
            **payload,
            'to': alert_email,
            'subject': f'[Novu Radar] {opportunity.band} lead ({opportunity.score}/100): {opportunity.requirement[:80]}',
            'body': (
                f"Requirement: {opportunity.requirement}\n"
                f"Company: {opportunity.company_name or 'Unknown'}\n"
                f"Score: {opportunity.score}/100 ({opportunity.band})\n"
                f"Status: {opportunity.status}\n"
                f"Source: {opportunity.source_url or 'n/a'}\n"
            ),
        })
