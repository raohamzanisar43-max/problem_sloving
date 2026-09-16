"""
Role isolation (handover §11, acceptance check "Role isolation").

Executives work the queue; managers create and merge; only administrators
delete. These are the boundaries the acceptance checklist depends on.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.opportunities.models import DuplicateCandidate, Opportunity

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


class RoleBoundaryTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='a', password='p', role='admin')
        self.manager = User.objects.create_user(username='m', password='p', role='sales_manager')
        self.executive = User.objects.create_user(username='e', password='p', role='sales_executive')
        self.opportunity = make_opportunity()

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_executive_cannot_delete_opportunity(self):
        resp = self.client_for(self.executive).delete(f'/api/v1/opportunities/{self.opportunity.id}/')
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Opportunity.objects.filter(pk=self.opportunity.pk).exists())

    def test_manager_cannot_delete_opportunity(self):
        resp = self.client_for(self.manager).delete(f'/api/v1/opportunities/{self.opportunity.id}/')
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_delete_opportunity(self):
        resp = self.client_for(self.admin).delete(f'/api/v1/opportunities/{self.opportunity.id}/')
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Opportunity.objects.filter(pk=self.opportunity.pk).exists())

    def test_executive_cannot_create_opportunity(self):
        resp = self.client_for(self.executive).post(
            '/api/v1/opportunities/', {'requirement': 'Injected'}, format='json',
        )
        self.assertEqual(resp.status_code, 403)

    def test_manager_can_create_opportunity(self):
        resp = self.client_for(self.manager).post(
            '/api/v1/opportunities/', {'requirement': 'Manager captured lead'}, format='json',
        )
        self.assertEqual(resp.status_code, 201)

    def test_executive_cannot_trigger_a_run(self):
        resp = self.client_for(self.executive).post('/api/v1/runs/', {}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_executive_cannot_change_source_credentials(self):
        from apps.sources.models import Source
        source = Source.objects.create(name='Feeds', connector_type='rss')
        resp = self.client_for(self.executive).patch(
            f'/api/v1/sources/{source.id}/', {'enabled': True}, format='json',
        )
        self.assertEqual(resp.status_code, 403)
        source.refresh_from_db()
        self.assertFalse(source.enabled)

    def test_executive_cannot_read_the_outbox(self):
        self.assertEqual(self.client_for(self.executive).get('/api/v1/outbox/').status_code, 403)

    def test_executive_cannot_resolve_duplicates(self):
        other = make_opportunity(requirement='Test ERP requirement (copy)')
        candidate = DuplicateCandidate.objects.create(
            opportunity_a=self.opportunity, opportunity_b=other, similarity=0.9,
        )
        resp = self.client_for(self.executive).post(
            f'/api/v1/duplicates/{candidate.id}/resolve/', {'decision': 'accepted'}, format='json',
        )
        self.assertEqual(resp.status_code, 403)
        candidate.refresh_from_db()
        self.assertEqual(candidate.decision, 'pending')


class DuplicateResolutionTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username='m2', password='p', role='sales_manager')
        self.client = APIClient()
        self.client.force_authenticate(self.manager)
        self.high = make_opportunity(requirement='ERP partner needed', score=80)
        self.low = make_opportunity(requirement='ERP partner required', score=40)
        self.candidate = DuplicateCandidate.objects.create(
            opportunity_a=self.high, opportunity_b=self.low, similarity=0.92,
        )

    def test_accepting_closes_the_lower_scored_record(self):
        resp = self.client.post(
            f'/api/v1/duplicates/{self.candidate.id}/resolve/', {'decision': 'accepted'}, format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.low.refresh_from_db()
        self.high.refresh_from_db()
        self.assertEqual(self.low.status, 'closed')
        self.assertEqual(self.high.status, 'new')
        self.assertIn(self.high.public_id, self.low.notes)

    def test_a_pair_cannot_be_resolved_twice(self):
        url = f'/api/v1/duplicates/{self.candidate.id}/resolve/'
        self.assertEqual(self.client.post(url, {'decision': 'accepted'}, format='json').status_code, 200)
        self.assertEqual(self.client.post(url, {'decision': 'rejected'}, format='json').status_code, 409)

    def test_decision_must_be_valid(self):
        resp = self.client.post(
            f'/api/v1/duplicates/{self.candidate.id}/resolve/', {'decision': 'maybe'}, format='json',
        )
        self.assertEqual(resp.status_code, 400)


class QueuePaginationTests(TestCase):
    """Every list endpoint must paginate without assuming an Opportunity field."""

    def setUp(self):
        self.admin = User.objects.create_user(username='a2', password='p', role='admin')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_every_list_endpoint_responds(self):
        for path in (
            '/api/v1/users/',
            '/api/v1/sources/',
            '/api/v1/search-terms/',
            '/api/v1/runs/',
            '/api/v1/observations/',
            '/api/v1/opportunities/',
            '/api/v1/duplicates/',
            '/api/v1/contacts/',
            '/api/v1/outbox/',
            '/api/v1/sync/jobs/',
            '/api/v1/sync/targets/',
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_queue_reports_a_total_count(self):
        make_opportunity()
        make_opportunity(requirement='Second')
        body = self.client.get('/api/v1/opportunities/').json()
        self.assertEqual(body['count'], 2)
        self.assertIn('results', body)
