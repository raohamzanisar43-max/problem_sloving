"""Reddit via Apify: client-post filter, collection (mocked Apify) and the queue source filter."""
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.observations.models import Observation
from apps.opportunities.models import Opportunity
from apps.sources.collectors.reddit_apify import RedditApifyCollector, is_client_post
from apps.sources.models import Source, SearchTerm
from apps.sources.tasks import collect_source

User = get_user_model()


def post(pid, title, body='', flair='', sub='forhire'):
    return {
        'type': 'post', 'id': pid, 'title': title, 'selfText': body, 'linkFlairText': flair,
        'subreddit': sub, 'author': 'someone', 'createdAt': '2026-11-23T06:00:00.000Z',
        'permalink': f'https://www.reddit.com/r/{sub}/comments/{pid}/x/',
    }


class ClientPostFilterTests(TestCase):
    def test_keeps_paid_software_requests(self):
        self.assertTrue(is_client_post('[Hiring] Need a Shopify store built', 'Budget $500', 'Hiring'))
        self.assertTrue(is_client_post('Looking for a WordPress developer to build a landing page', '$59'))

    def test_drops_sellers_cofounders_and_non_software(self):
        self.assertFalse(is_client_post('[For Hire] Full-Stack Developer $20/hr', '', 'For Hire'))
        self.assertFalse(is_client_post('[Offer] Go backend development', '', 'Offer'))
        self.assertFalse(is_client_post('Looking for a technical co-founder for my app', 'equity only'))
        self.assertFalse(is_client_post('[Hiring] Native Korean translator needed', 'per chapter', 'Hiring'))
        self.assertFalse(is_client_post('[HIRING] VA to warm up TikTok accounts', 'paid trial', 'Hiring'))


@override_settings(RADAR={**__import__('django.conf', fromlist=['settings']).settings.RADAR,
                          'APIFY_TOKEN': 'test-token', 'LLM_PROVIDER': 'stub'})
class RedditCollectionTests(TestCase):
    def setUp(self):
        Source.objects.filter(connector_type='reddit').delete()
        self.web = Source.objects.filter(connector_type='web_search').first() or Source.objects.create(
            name='Web search', connector_type='web_search', enabled=False, access_state='ready')
        SearchTerm.objects.create(source=self.web, query='shopify store developer', market='PK', enabled=True)
        self.source = Source.objects.create(name='Reddit', connector_type='reddit', enabled=True,
                                            access_state='ready', settings={})

    def fake_apify(self, *args, **kwargs):
        actor_input = kwargs['json']
        response = mock.Mock()
        response.raise_for_status = lambda: None
        if 'urls' in actor_input:
            response.json = lambda: [
                post('a1', '[Hiring] Need a Shopify store developer for my clothing brand',
                     'Budget $800. Must know Shopify themes.', 'Hiring'),
                post('a2', '[For Hire] Shopify developer available', '', 'For Hire'),
            ]
        else:
            response.json = lambda: [
                post('a1', '[Hiring] Need a Shopify store developer for my clothing brand',
                     'Budget $800.', 'Hiring'),  # duplicate of the listing result
                post('b1', 'Looking for a technical co-founder', 'equity', sub='startups'),
            ]
        return response

    def test_collects_only_client_posts_once_and_uses_settings_keywords(self):
        with mock.patch('apps.sources.collectors.reddit_apify.httpx.post', side_effect=self.fake_apify) as call:
            counters = collect_source(str(self.source.id))
        self.assertEqual(call.call_count, 2)  # one listing run + one search run, not one per keyword
        first_input = call.call_args_list[0].kwargs['json']
        self.assertEqual(first_input['postedAfter'], '3 days')
        self.assertEqual(first_input['filterKeywords'], ['hiring', 'task'])
        self.assertEqual(counters['new'], 1)
        self.assertEqual(Observation.objects.filter(source=self.source).count(), 1)
        self.assertTrue(Opportunity.objects.filter(source_url__contains='/comments/a1/').exists())

    def test_later_runs_only_look_back_since_last_run(self):
        with mock.patch('apps.sources.collectors.reddit_apify.httpx.post', side_effect=self.fake_apify):
            collect_source(str(self.source.id))
        with mock.patch('apps.sources.collectors.reddit_apify.httpx.post', side_effect=self.fake_apify) as call:
            collect_source(str(self.source.id))
        self.assertEqual(call.call_args_list[0].kwargs['json']['postedAfter'], '14 hours')

    @override_settings(RADAR={**__import__('django.conf', fromlist=['settings']).settings.RADAR, 'APIFY_TOKEN': ''})
    def test_missing_token_is_reported_without_calling_apify(self):
        with mock.patch('apps.sources.collectors.reddit_apify.httpx.post') as call:
            counters = collect_source(str(self.source.id))
        call.assert_not_called()
        self.assertEqual(counters['errors'], 1)


class RedditSourceFilterTests(TestCase):
    def test_queue_source_filter(self):
        client = APIClient()
        client.force_authenticate(User.objects.create_user(username='m', password='p', role='sales_manager'))
        Opportunity.objects.create(requirement='Reddit lead', text='x', score=70, band='Hot', status='new',
                                   source_url='https://www.reddit.com/r/forhire/comments/a1/x/')
        Opportunity.objects.create(requirement='Freelancer lead', text='x', score=70, band='Hot', status='new',
                                   source_url='https://www.freelancer.com/projects/x/y')
        Opportunity.objects.create(requirement='Web lead', text='x', score=70, band='Hot', status='new',
                                   source_url='https://example.com/post')

        def titles(source):
            return [o['requirement'] for o in client.get('/api/v1/opportunities/', {'source': source}).json()['results']]

        self.assertEqual(titles('reddit'), ['Reddit lead'])
        self.assertEqual(titles('web'), ['Web lead'])
