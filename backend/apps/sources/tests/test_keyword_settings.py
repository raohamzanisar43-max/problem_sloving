"""Search keywords and ignore words managed from the Settings screen."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.opportunities.models import Opportunity
from apps.sources.models import SearchTerm, Source

User = get_user_model()


def make_lead(**kwargs):
    defaults = dict(
        requirement='Need someone to build my website',
        text='Looking for a developer to build my online store. Budget $500.',
        intent='buyer', kind='direct_purchase', score=70, band='High potential',
        status='review', source_url='https://www.reddit.com/r/forhire/comments/abc/need/',
    )
    defaults.update(kwargs)
    return Opportunity.objects.create(**defaults)


class SearchKeywordApiTests(TestCase):
    def setUp(self):
        self.web = Source.objects.create(name='Web search', connector_type='web_search', enabled=True)
        # A superuser keeps full access even with a sales_executive role.
        self.owner = User.objects.create_user(
            username='owner', password='p', role='sales_executive', is_superuser=True,
        )
        self.executive = User.objects.create_user(username='exec', password='p', role='sales_executive')
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def test_add_keyword_goes_to_web_search_source(self):
        resp = self.client.post('/api/v1/search-terms/', {'query': '  need a   website built '}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        term = SearchTerm.objects.get()
        self.assertEqual(term.query, 'need a website built')
        self.assertEqual(term.source, self.web)
        self.assertEqual(term.group_name, 'Custom keywords')
        self.assertTrue(term.enabled)

    def test_duplicate_and_empty_keywords_are_refused(self):
        self.client.post('/api/v1/search-terms/', {'query': 'need an app developer'}, format='json')
        dup = self.client.post('/api/v1/search-terms/', {'query': 'Need An App Developer'}, format='json')
        self.assertEqual(dup.status_code, 400)
        empty = self.client.post('/api/v1/search-terms/', {'query': '   '}, format='json')
        self.assertEqual(empty.status_code, 400)

    def test_switch_off_list_all_and_delete(self):
        term = SearchTerm.objects.create(source=self.web, group_name='G', query='need a developer')
        resp = self.client.patch(f'/api/v1/search-terms/{term.id}/', {'enabled': False}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.get('/api/v1/search-terms/').json()['count'], 0)
        self.assertEqual(self.client.get('/api/v1/search-terms/?all=1').json()['count'], 1)
        self.assertEqual(self.client.delete(f'/api/v1/search-terms/{term.id}/').status_code, 204)
        self.assertFalse(SearchTerm.objects.exists())

    def test_sales_executive_can_read_but_not_change(self):
        self.client.force_authenticate(self.executive)
        self.assertEqual(self.client.get('/api/v1/search-terms/').status_code, 200)
        resp = self.client.post('/api/v1/search-terms/', {'query': 'need a developer'}, format='json')
        self.assertEqual(resp.status_code, 403)


class IgnoreKeywordsApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner', password='p', role='sales_executive', is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def test_defaults_are_returned_until_saved(self):
        keywords = self.client.get('/api/v1/ignore-keywords/').json()['keywords']
        self.assertIn('how to find', keywords)

    def test_saving_hides_matching_leads_and_removing_restores_them(self):
        lead = make_lead()
        other = make_lead(requirement='Need a mobile app built', text='Looking for a developer for my app.')

        resp = self.client.put('/api/v1/ignore-keywords/', {'keywords': ['Online Store', 'online store']}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()['keywords'], ['online store'])
        self.assertEqual(resp.json()['rejected'], 1)
        lead.refresh_from_db(); other.refresh_from_db()
        self.assertEqual(lead.status, 'rejected')
        self.assertEqual(other.status, 'review')

        resp = self.client.put('/api/v1/ignore-keywords/', {'keywords': []}, format='json')
        self.assertEqual(resp.json()['restored'], 1)
        lead.refresh_from_db()
        self.assertEqual(lead.status, 'review')
        self.assertEqual(lead.review_reasons, [])

    def test_leads_rejected_by_a_person_are_never_restored(self):
        lead = make_lead(status='rejected', review_reasons=['Rejected by sales'])
        self.client.put('/api/v1/ignore-keywords/', {'keywords': []}, format='json')
        lead.refresh_from_db()
        self.assertEqual(lead.status, 'rejected')

    def test_bad_payload_and_permissions(self):
        self.assertEqual(self.client.put('/api/v1/ignore-keywords/', {'keywords': 'x'}, format='json').status_code, 400)
        executive = User.objects.create_user(username='exec', password='p', role='sales_executive')
        self.client.force_authenticate(executive)
        self.assertEqual(self.client.get('/api/v1/ignore-keywords/').status_code, 200)
        self.assertEqual(self.client.put('/api/v1/ignore-keywords/', {'keywords': []}, format='json').status_code, 403)
