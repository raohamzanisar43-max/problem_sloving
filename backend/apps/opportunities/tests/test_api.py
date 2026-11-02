"""
Integration tests for Opportunity REST API.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.opportunities.models import Opportunity
from apps.scoring.engine import compute_score
from django.utils import timezone

User = get_user_model()


def make_opportunity(**kwargs):
    defaults = dict(
        requirement='Test ERP requirement',
        text='We need an ERP system for our 200 staff.',
        intent='buyer',
        kind='direct_purchase',
        primary_category='ERP',
        categories=['ERP'],
        score=75,
        band='High potential',
        status='new',
    )
    defaults.update(kwargs)
    return Opportunity.objects.create(**defaults)


class AuthTests(TestCase):
    def test_unauthenticated_returns_401(self):
        client = APIClient()
        resp = client.get('/api/v1/opportunities/')
        self.assertEqual(resp.status_code, 401)


class OpportunityListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='manager', password='pass', role='sales_manager'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.opp = make_opportunity()

    def test_list_returns_opportunities(self):
        resp = self.client.get('/api/v1/opportunities/')
        self.assertEqual(resp.status_code, 200)
        # Cursor pagination returns 'results' key
        data = resp.json()
        self.assertIn('results', data)
        self.assertGreaterEqual(len(data['results']), 1)

    def test_filter_by_status(self):
        make_opportunity(requirement='Closed', status='closed')
        resp = self.client.get('/api/v1/opportunities/', {'status': 'new'})
        self.assertEqual(resp.status_code, 200)
        for item in resp.json().get('results', []):
            self.assertEqual(item['status'], 'new')

    def test_search_filter(self):
        make_opportunity(requirement='Mobile app for school management', status='new')
        resp = self.client.get('/api/v1/opportunities/', {'search': 'school'})
        self.assertEqual(resp.status_code, 200)
        results = resp.json().get('results', [])
        self.assertTrue(any('school' in r['requirement'].lower() for r in results))


class OpportunityDetailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='manager2', password='pass', role='sales_manager'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.opp = make_opportunity()

    def test_detail_returns_score_breakdown(self):
        resp = self.client.get(f'/api/v1/opportunities/{self.opp.id}/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('score', data)
        self.assertIn('band', data)

    def test_patch_status(self):
        resp = self.client.patch(
            f'/api/v1/opportunities/{self.opp.id}/',
            {'status': 'reviewed', 'expected_revision': self.opp.revision},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.status, 'reviewed')

    def test_patch_corrects_extracted_details(self):
        resp = self.client.patch(
            f'/api/v1/opportunities/{self.opp.id}/',
            {
                'company_name': 'Acme Traders',
                'country': 'Pakistan',
                'deadline': '2026-12-31',
                'email': 'buyer@acme.example',
                'expected_revision': self.opp.revision,
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['company_name'], 'Acme Traders')
        self.assertEqual(data['deadline'], '2026-12-31')
        # A hand-typed address is labelled as such, never as published.
        self.assertEqual(data['contact_verification'], 'manual')
        self.assertTrue(
            self.opp.activities.filter(action='company_name_change', to_value='Acme Traders').exists()
        )

    def test_patch_cannot_change_score_or_evidence(self):
        self.client.patch(
            f'/api/v1/opportunities/{self.opp.id}/',
            {'score': 100, 'text': 'rewritten', 'source_url': 'https://evil.example'},
            format='json',
        )
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.score, 75)
        self.assertEqual(self.opp.text, 'We need an ERP system for our 200 staff.')
        self.assertEqual(self.opp.source_url, '')


class StatsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='manager3', password='pass', role='sales_manager'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        make_opportunity(intent='buyer', status='new')
        make_opportunity(intent='uncertain', status='review')

    def test_stats_endpoint(self):
        resp = self.client.get('/api/v1/opportunities/stats/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('collected', data)
        self.assertIn('explicit_buyers', data)
        self.assertIn('awaiting_review', data)


class PipelineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='manager4', password='pass', role='sales_manager'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        make_opportunity(status='reviewed')
        make_opportunity(status='contacted')

    def test_pipeline_endpoint(self):
        resp = self.client.get('/api/v1/opportunities/pipeline/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('reviewed', data)
        self.assertIn('contacted', data)
        self.assertIsInstance(data['reviewed'], list)

