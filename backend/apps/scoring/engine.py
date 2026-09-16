"""
Deterministic 100-point scoring engine (handover §7).

Factor max points:
  Buying intent 30 · Service match 25 · Recency 15 · Evidence quality 15 · Contact path 10 · Deadline urgency 5
"""
from datetime import date, datetime, timezone as dt_timezone
from django.utils import timezone


SERVICE_CATEGORIES = {
    'CUSTOM_DEV', 'MOBILE_APP', 'WEBSITE', 'ERP', 'CRM', 'LMS',
    'AI_AUTOMATION', 'STAFF_AUGMENTATION', 'MANAGED_IT', 'CLOUD_DEVOPS', 'CYBERSECURITY',
}


def as_date(value):
    """
    Coerce a date, datetime or ISO-8601 string to a `date`.

    Extraction output arrives as a JSON string ("2026-09-10"), so every caller
    that compares deadlines has to tolerate that form as well as real objects.
    Returns None when the value is missing or unparseable.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace('Z', '+00:00')).date()
        except ValueError:
            return None
    return None


def _days_ago(dt):
    if not dt:
        return None
    if isinstance(dt, str):
        parsed = as_date(dt)
        if parsed is None:
            return None
        dt = datetime(parsed.year, parsed.month, parsed.day, tzinfo=dt_timezone.utc)
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime(dt.year, dt.month, dt.day, tzinfo=dt_timezone.utc)
    now = timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, dt_timezone.utc)
    return (now - dt).days


def score_buying_intent(intent: str, kind: str) -> int:
    if intent == 'nonbuyer' or kind == 'seller_promotion':
        return 0
    if kind in ('direct_purchase', 'rfp'):
        return 30
    if kind == 'agency_staffing':
        return 24
    if kind == 'indirect_pain':
        return 10
    if kind == 'hiring_signal':
        return 5
    if intent == 'buyer':
        return 30
    return 0


def score_service_match(categories: list) -> int:
    if not categories:
        return 0
    for c in categories:
        if c in SERVICE_CATEGORIES:
            return 25
    return 0


def score_recency(published_at) -> int:
    days = _days_ago(published_at)
    if days is None:
        return 0
    if days < 0:
        return 0  # future date
    if days <= 2:
        return 15
    if days <= 7:
        return 10
    if days <= 30:
        return 5
    return 0


def score_evidence(has_quote: bool, has_full_text: bool) -> int:
    pts = 0
    if has_quote:
        pts += 10
    if has_full_text:
        pts += 5
    return pts


def score_contact(has_email_or_phone: bool, has_source_url: bool) -> int:
    if has_email_or_phone:
        return 10
    if has_source_url:
        return 3
    return 0


def score_deadline(deadline, published_at=None) -> int:
    deadline = as_date(deadline)
    if not deadline:
        return 0
    today = timezone.now().date()
    if deadline < today:
        return 0  # expired handled by status override
    delta = (deadline - today).days
    if delta <= 7:
        return 5
    return 0


def compute_score(
    *,
    intent: str = 'uncertain',
    kind: str = 'other',
    categories: list | None = None,
    published_at=None,
    has_quote: bool = True,
    has_full_text: bool = True,
    email: str = '',
    phone: str = '',
    source_url: str = '',
    deadline=None,
) -> dict:
    """
    Returns dict with score, band, factors list, review_reasons, status_override.
    """
    categories = categories or []
    deadline = as_date(deadline)
    factors = [
        score_buying_intent(intent, kind),
        score_service_match(categories),
        score_recency(published_at),
        score_evidence(has_quote, has_full_text),
        score_contact(bool(email or phone), bool(source_url)),
        score_deadline(deadline, published_at),
    ]
    total = sum(factors)

    review_reasons = []
    status_override = None

    if intent == 'nonbuyer' or kind == 'seller_promotion':
        status_override = 'rejected'
        review_reasons.append('Seller promotion; no buyer requirement')
        total = 0
    elif deadline and deadline < timezone.now().date():
        status_override = 'closed'
        review_reasons.append('Deadline expired')
    elif kind == 'hiring_signal' or intent == 'uncertain':
        status_override = 'review'
        if kind == 'hiring_signal':
            review_reasons.append('Purchase intent requires review')
            review_reasons.append('Uncertain buying intent')
        else:
            review_reasons.append('Uncertain buying intent')

    if total >= 80:
        band = 'Hot'
    elif total >= 60:
        band = 'High potential'
    elif total >= 40:
        band = 'Review'
    else:
        band = 'Archive'

    return {
        'score': total,
        'band': band,
        'factors': factors,
        'review_reasons': review_reasons,
        'status_override': status_override,
    }
