"""
Deterministic scoring engine (handover §7).

Factor maxima: intent 30 · service 25 · recency 15 · evidence 15 · contact 10 · deadline 5
"""
from datetime import date, datetime, timedelta, timezone

from django.test import SimpleTestCase

from apps.scoring.engine import (
    as_date,
    compute_score,
    score_buying_intent,
    score_service_match,
)


class ScoringPolicyTests(SimpleTestCase):
    """The worked examples from the handover."""

    def test_explicit_erp_with_email(self):
        result = compute_score(
            intent='buyer',
            kind='direct_purchase',
            categories=['ERP'],
            published_at=datetime.now(timezone.utc) - timedelta(days=1),
            has_quote=True,
            has_full_text=True,
            email='procurement@example.invalid',
            source_url='https://example.invalid/1',
        )
        self.assertEqual(result['score'], 95)
        self.assertEqual(result['band'], 'Hot')
        self.assertIsNone(result['status_override'])

    def test_without_email_falls_back_to_source_url(self):
        result = compute_score(
            intent='buyer',
            kind='direct_purchase',
            categories=['MANAGED_IT'],
            published_at=datetime.now(timezone.utc) - timedelta(days=1),
            has_quote=True,
            has_full_text=True,
            email='',
            source_url='https://example.invalid/2',
        )
        self.assertEqual(result['score'], 88)

    def test_hiring_signal_is_held_for_review(self):
        result = compute_score(
            intent='uncertain',
            kind='hiring_signal',
            categories=['MOBILE_APP'],
            published_at=datetime.now(timezone.utc) - timedelta(days=1),
            has_quote=True,
            has_full_text=True,
            source_url='https://example.invalid/3',
        )
        self.assertEqual(result['status_override'], 'review')
        self.assertIn('Purchase intent requires review', result['review_reasons'])

    def test_seller_promotion_is_rejected(self):
        result = compute_score(
            intent='nonbuyer',
            kind='seller_promotion',
            categories=['WEBSITE'],
            published_at=datetime.now(timezone.utc),
            has_quote=True,
            has_full_text=True,
        )
        self.assertEqual(result['status_override'], 'rejected')
        self.assertEqual(result['factors'][0], 0)
        self.assertEqual(result['score'], 0)

    def test_expired_tender_is_closed(self):
        result = compute_score(
            intent='buyer',
            kind='rfp',
            categories=['LMS'],
            published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            has_quote=True,
            has_full_text=True,
            deadline=date(2020, 1, 1),
            source_url='https://example.invalid/5',
        )
        self.assertEqual(result['status_override'], 'closed')

    def test_factors_always_sum_to_score(self):
        result = compute_score(
            intent='buyer',
            kind='rfp',
            categories=['CRM'],
            published_at=datetime.now(timezone.utc),
            has_quote=True,
            has_full_text=True,
            email='buyer@example.invalid',
            source_url='https://example.invalid/6',
        )
        self.assertEqual(sum(result['factors']), result['score'])


class EdgeCaseTests(SimpleTestCase):
    def test_nonbuyer_always_scores_zero_intent(self):
        self.assertEqual(score_buying_intent('nonbuyer', 'direct_purchase'), 0)

    def test_seller_promotion_always_scores_zero(self):
        result = compute_score(intent='buyer', kind='seller_promotion')
        self.assertEqual(result['score'], 0)
        self.assertEqual(result['status_override'], 'rejected')

    def test_max_score_possible(self):
        result = compute_score(
            intent='buyer',
            kind='direct_purchase',
            categories=['ERP'],
            published_at=datetime.now(timezone.utc),
            has_quote=True,
            has_full_text=True,
            email='buyer@example.com',
            source_url='https://example.com',
            deadline=datetime.now(timezone.utc).date(),
        )
        self.assertEqual(result['score'], 100)
        self.assertEqual(result['band'], 'Hot')

    def test_expired_deadline_closed(self):
        result = compute_score(
            intent='buyer',
            kind='rfp',
            categories=['LMS'],
            published_at=datetime.now(timezone.utc),
            has_quote=True,
            has_full_text=True,
            deadline=datetime.now(timezone.utc).date() - timedelta(days=1),
        )
        self.assertEqual(result['status_override'], 'closed')

    def test_hiring_signal_goes_to_review(self):
        result = compute_score(intent='uncertain', kind='hiring_signal')
        self.assertEqual(result['status_override'], 'review')
        self.assertTrue(result['review_reasons'])

    def test_no_categories_zero_service_score(self):
        self.assertEqual(score_service_match([]), 0)
        self.assertEqual(score_service_match(['UNKNOWN_CAT']), 0)

    def test_archive_band_for_low_score(self):
        self.assertEqual(compute_score(intent='uncertain', kind='other')['band'], 'Archive')


class DateCoercionTests(SimpleTestCase):
    """Extraction returns JSON strings, so every date input must be tolerated."""

    def test_iso_string_deadline_scores(self):
        soon = (datetime.now(timezone.utc).date() + timedelta(days=3)).isoformat()
        result = compute_score(
            intent='buyer', kind='rfp', categories=['ERP'], deadline=soon,
        )
        self.assertEqual(result['factors'][5], 5)

    def test_expired_iso_string_deadline_closes(self):
        past = (datetime.now(timezone.utc).date() - timedelta(days=3)).isoformat()
        result = compute_score(
            intent='buyer', kind='rfp', categories=['ERP'], deadline=past,
        )
        self.assertEqual(result['status_override'], 'closed')

    def test_unparseable_date_is_ignored_not_fatal(self):
        self.assertIsNone(as_date('next Tuesday'))
        result = compute_score(intent='buyer', kind='rfp', deadline='next Tuesday')
        self.assertEqual(result['factors'][5], 0)
        self.assertIsNone(result['status_override'])

    def test_blank_and_none_are_none(self):
        self.assertIsNone(as_date(''))
        self.assertIsNone(as_date(None))
