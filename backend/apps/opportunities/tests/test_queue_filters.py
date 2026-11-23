"""Opportunity queue filters: posted window, newest-first sort, min score, source."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.opportunities.models import Opportunity

User = get_user_model()


def make(title, days_ago, score=70, url='https://example.com/post', **kw):
    published = timezone.now() - timedelta(days=days_ago)
    return Opportunity.objects.create(
        requirement=title, text=title, score=score, band='Hot', status='new',
        source_url=url, source_published_at=published, **kw,
    )


class QueueFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create_user(username='m', password='p', role='sales_manager'))
        self.today = make('Today app', 0, score=60, url='https://www.freelancer.com/projects/x/today-app')
        self.week = make('Week app', 3, score=90)
        self.month = make('Month app', 20, score=80)
        self.old = make('Old app', 60, score=95)

    def titles(self, **params):
        data = self.client.get('/api/v1/opportunities/', params).json()
        return [o['requirement'] for o in data['results']]

    def test_posted_windows(self):
        self.assertEqual(self.titles(posted='today'), ['Today app'])
        self.assertEqual(set(self.titles(posted='week')), {'Today app', 'Week app'})
        self.assertEqual(set(self.titles(posted='month')), {'Today app', 'Week app', 'Month app'})
        self.assertEqual(self.titles(posted='older'), ['Old app'])

    def test_newest_first_sort(self):
        self.assertEqual(self.titles(ordering='-posted_at'), ['Today app', 'Week app', 'Month app', 'Old app'])
        self.assertEqual(self.titles(ordering='-score')[0], 'Old app')

    def test_min_score_is_server_side(self):
        self.assertEqual(set(self.titles(min_score=85)), {'Week app', 'Old app'})

    def test_source_filter(self):
        self.assertEqual(self.titles(source='freelancer'), ['Today app'])
        self.assertNotIn('Today app', self.titles(source='web'))

    def test_newest_sort_pages_without_gaps(self):
        for i in range(30):
            make(f'Bulk {i}', 1)
        first = self.client.get('/api/v1/opportunities/', {'ordering': '-posted_at'}).json()
        second = self.client.get(first['next']).json()
        ids = [o['id'] for o in first['results'] + second['results']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 34)
