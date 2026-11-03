"""
Posted-date recency: the `posted` filter and the stats counts (today / last 7 days / last 30 days).
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.opportunities.models import Opportunity

User = get_user_model()


def lead(label, published_days_ago=None, detected_days_ago=0, status='new'):
    now = timezone.now()
    return Opportunity.objects.create(
        requirement=label,
        text=label,
        intent='buyer',
        kind='direct_purchase',
        score=70,
        band='High potential',
        status=status,
        source_published_at=None if published_days_ago is None else now - timedelta(days=published_days_ago),
        detected_at=now - timedelta(days=detected_days_ago),
    )


class RecencyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create_user(username='mgr', password='x', role='sales_manager'))
        lead('fresh', published_days_ago=0)
        lead('this-week', published_days_ago=3)
        lead('this-month', published_days_ago=20)
        lead('old', published_days_ago=90)
        # Source gave no date: the detection date is used instead.
        lead('undated-recent', published_days_ago=None, detected_days_ago=1)
        lead('rejected-fresh', published_days_ago=0, status='rejected')

    def names(self, posted):
        resp = self.client.get('/api/v1/opportunities/', {'posted': posted})
        self.assertEqual(resp.status_code, 200)
        return {o['requirement'] for o in resp.json()['results']}

    def test_today_window(self):
        self.assertIn('fresh', self.names('today'))
        self.assertNotIn('this-week', self.names('today'))

    def test_week_window_includes_today(self):
        got = self.names('week')
        self.assertTrue({'fresh', 'this-week', 'undated-recent'} <= got)
        self.assertNotIn('this-month', got)

    def test_month_window(self):
        got = self.names('month')
        self.assertIn('this-month', got)
        self.assertNotIn('old', got)

    def test_older_window(self):
        self.assertEqual(self.names('older'), {'old'})

    def test_invalid_value_is_rejected(self):
        resp = self.client.get('/api/v1/opportunities/', {'posted': 'yesterday-ish'})
        self.assertEqual(resp.status_code, 400)

    def test_stats_count_only_actionable_leads(self):
        posted = self.client.get('/api/v1/opportunities/stats/').json()['posted']
        # rejected-fresh is excluded everywhere.
        self.assertEqual(posted['today'], 1)
        self.assertEqual(posted['week'], 3)
        self.assertEqual(posted['month'], 4)
        self.assertEqual(posted['older'], 1)
