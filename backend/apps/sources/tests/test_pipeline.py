"""
Collection pipeline: dedupe, partial failure, run lifecycle and duplicate scan.
"""
from datetime import datetime, timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.observations.models import Observation
from apps.opportunities.models import DuplicateCandidate, Opportunity
from apps.sources.collectors.base import BaseCollector
from apps.sources.models import Run, SearchTerm, Source
from apps.sources.tasks import collect_source, find_duplicates

User = get_user_model()


class FakeCollector(BaseCollector):
    """Returns canned rows; raises for any term containing 'boom'."""
    rows_by_term = {}

    def fetch_observations(self, term_query, market='PK'):
        if 'boom' in term_query:
            raise RuntimeError('connector exploded')
        return self.rows_by_term.get(term_query, [])


def row(**kwargs):
    base = {
        'external_id': '',
        'original_url': 'https://example.invalid/a',
        'canonical_url': 'https://example.invalid/a',
        'title': 'ERP partner needed',
        'text': 'We need an ERP development partner for fleet operations.',
        'author': '',
        'source_published_at': datetime(2026, 9, 15, tzinfo=timezone.utc),
        'raw_payload': {},
    }
    base.update(kwargs)
    return base


class CollectorDedupeTests(TestCase):
    def setUp(self):
        self.source = Source.objects.create(name='Feeds', connector_type='rss', enabled=True)
        self.run = Run.objects.create(source=self.source, state='queued')
        self.collector = FakeCollector(self.source)

    def test_rows_with_external_id_dedupe_on_replay(self):
        self.collector.rows_by_term = {'q': [row(external_id='abc'), row(external_id='abc')]}
        term = SearchTerm.objects.create(group_name='g', query='q')
        fetched, created, duplicates, errors = self.collector.run(self.run, [term])
        self.assertEqual((fetched, created, duplicates), (2, 1, 1))
        self.assertEqual(errors, [])
        self.assertEqual(Observation.objects.count(), 1)

    def test_rows_without_external_id_still_dedupe_by_url(self):
        # A blank external_id is excluded from the unique constraint, so two
        # genuinely different rows must not collapse onto one record, and the
        # same row twice must not create two.
        self.collector.rows_by_term = {
            'q': [
                row(original_url='https://example.invalid/one', canonical_url='https://example.invalid/one'),
                row(original_url='https://example.invalid/two', canonical_url='https://example.invalid/two'),
                row(original_url='https://example.invalid/one', canonical_url='https://example.invalid/one'),
            ]
        }
        term = SearchTerm.objects.create(group_name='g', query='q')
        fetched, created, duplicates, _ = self.collector.run(self.run, [term])
        self.assertEqual((fetched, created, duplicates), (3, 2, 1))
        self.assertEqual(Observation.objects.count(), 2)

    def test_one_failing_term_does_not_stop_the_others(self):
        self.collector.rows_by_term = {'ok': [row(external_id='x')]}
        terms = [
            SearchTerm.objects.create(group_name='g', query='boom'),
            SearchTerm.objects.create(group_name='g', query='ok'),
        ]
        fetched, created, _, errors = self.collector.run(self.run, terms)
        self.assertEqual(created, 1)
        self.assertEqual(len(errors), 1)
        self.source.refresh_from_db()
        # A run that hit an error is not recorded as a clean success.
        self.assertIsNone(self.source.last_success_at)
        self.assertIn('connector exploded', self.source.last_error)


class RunLifecycleTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username='m5', password='p', role='sales_manager')
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def test_manual_trigger_creates_exactly_one_run(self):
        source = Source.objects.create(name='Feeds', connector_type='rss', enabled=True)
        resp = self.client.post('/api/v1/runs/', {'source_id': str(source.id)}, format='json')
        self.assertEqual(resp.status_code, 202)
        self.assertEqual(Run.objects.filter(source=source).count(), 1)

    def test_disabled_source_is_refused(self):
        source = Source.objects.create(name='X', connector_type='x', enabled=False)
        resp = self.client.post('/api/v1/runs/', {'source_id': str(source.id)}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('not enabled', resp.json()['detail'])

    def test_unknown_source_is_refused(self):
        resp = self.client.post('/api/v1/runs/', {'source_id': 'not-a-uuid'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_collect_source_reuses_a_supplied_run(self):
        source = Source.objects.create(name='Feeds', connector_type='rss', enabled=True)
        run = Run.objects.create(source=source, state='queued', trigger='manual')
        collect_source(str(source.id), run_id=str(run.id))
        self.assertEqual(Run.objects.count(), 1)
        run.refresh_from_db()
        self.assertIn(run.state, ('completed', 'partial'))
        self.assertIn('fetched', run.counters)

    def test_an_unloadable_collector_fails_only_its_own_run(self):
        source = Source.objects.create(name='Feeds', connector_type='rss', enabled=True)
        run = Run.objects.create(source=source, state='queued')
        with patch('apps.sources.tasks._import_collector', side_effect=ImportError('No module named feedparser')):
            collect_source(str(source.id), run_id=str(run.id))
        run.refresh_from_db()
        source.refresh_from_db()
        self.assertEqual(run.state, 'failed')
        self.assertIn('Collector unavailable', run.error)
        self.assertIn('feedparser', source.last_error)

    def test_disabled_source_run_completes_with_a_reason(self):
        source = Source.objects.create(name='Off', connector_type='rss', enabled=False)
        run = Run.objects.create(source=source, state='queued')
        collect_source(str(source.id), run_id=str(run.id))
        run.refresh_from_db()
        self.assertEqual(run.state, 'completed')
        self.assertEqual(run.counters.get('skipped'), 'source disabled')


class DuplicateScanTests(TestCase):
    def test_the_same_posting_seen_twice_is_paired(self):
        # The common real case: one requirement picked up by two connectors.
        Opportunity.objects.create(
            requirement='ERP development partner for fleet operations',
            source_name='web_search', score=80,
        )
        Opportunity.objects.create(
            requirement='ERP development partner for fleet operations',
            source_name='rss', score=60,
        )
        self.assertEqual(find_duplicates(), 1)
        self.assertEqual(DuplicateCandidate.objects.count(), 1)

    def test_a_reworded_posting_needs_a_lower_threshold(self):
        # Accepting a pair closes a lead, so the 0.80 default is deliberately
        # conservative: a reworded duplicate is only caught once an operator
        # lowers the threshold on the Settings screen.
        Opportunity.objects.create(requirement='ERP development partner for fleet operations', score=80)
        Opportunity.objects.create(requirement='ERP development partner for fleet operation', score=60)
        self.assertEqual(find_duplicates(), 0)
        self.assertEqual(find_duplicates(threshold=0.6), 1)

    def test_unrelated_requirements_are_not_paired(self):
        Opportunity.objects.create(requirement='ERP development partner for fleet operations', score=80)
        Opportunity.objects.create(requirement='Cybersecurity audit for a hospital network', score=60)
        self.assertEqual(find_duplicates(), 0)

    def test_the_scan_is_idempotent(self):
        Opportunity.objects.create(requirement='Mobile app for school management', score=80)
        Opportunity.objects.create(requirement='Mobile app for school management', score=60)
        find_duplicates()
        self.assertEqual(find_duplicates(), 0)
        self.assertEqual(DuplicateCandidate.objects.count(), 1)

    def test_closed_and_rejected_records_are_excluded(self):
        Opportunity.objects.create(requirement='Mobile app for school management', score=80, status='rejected')
        Opportunity.objects.create(requirement='Mobile app for school management', score=60, status='closed')
        self.assertEqual(find_duplicates(), 0)

    def test_a_single_record_is_not_a_pair(self):
        Opportunity.objects.create(requirement='Only one', score=50)
        self.assertEqual(find_duplicates(), 0)
