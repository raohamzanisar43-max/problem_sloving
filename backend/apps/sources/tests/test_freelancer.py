"""Freelancer.com collector: only software projects matching the keywords become leads."""
import time
from unittest import mock

from django.test import TestCase

from apps.opportunities.models import Opportunity
from apps.sources.collectors.freelancer import budget_text, is_software_project, search_query
from apps.sources.models import Run, SearchTerm, Source

IT = {'id': 1, 'name': 'Websites, IT & Software'}
MOBILE = {'id': 2, 'name': 'Mobile Phones & Computing'}
DESIGN = {'id': 3, 'name': 'Design, Media & Architecture'}
MARKETING = {'id': 4, 'name': 'Sales & Marketing'}


def job(name, category):
    return {'name': name, 'seo_url': name.lower().replace(' ', '_'), 'category': category}


def project(pid, title, jobs, description='', currency='USD', rate=1.0, low=250.0, high=750.0, kind='fixed', age_hours=2):
    return {
        'id': pid, 'title': title, 'description': description or f'{title}. Details inside.',
        'seo_url': f'{jobs[0]["seo_url"]}/{title.replace(" ", "-")}', 'type': kind,
        'budget': {'minimum': low, 'maximum': high},
        'currency': {'code': currency, 'sign': '$', 'exchange_rate': rate},
        'time_submitted': int(time.time() - age_hours * 3600),
        'frontend_project_status': 'open', 'jobs': jobs, 'bid_stats': {'bid_count': 4},
    }


FEED = [
    project(1, 'Build Flutter food delivery app', [job('Mobile App Development', MOBILE), job('Flutter', MOBILE), job('Android', MOBILE)]),
    project(2, 'Fresh logo for packaging', [job('Graphic Design', DESIGN), job('Logo Design', DESIGN), job('PHP', IT)]),
    project(3, 'Meta ads lead campaign', [job('PHP', IT), job('Internet Marketing', MARKETING), job('Facebook Marketing', MARKETING), job('SEO', IT)]),
    project(4, 'Restaurant website with booking', [job('PHP', IT), job('Website Design', DESIGN), job('WordPress', IT)],
            currency='INR', rate=0.0106, low=12500, high=37500),
    project(5, 'Old mobile app bug fix', [job('Android', MOBILE)], age_hours=24 * 30),
]


def fake_response(projects):
    resp = mock.Mock(status_code=200)
    resp.raise_for_status.return_value = None
    resp.json.return_value = {'status': 'success', 'result': {'projects': projects}}
    return resp


class FreelancerHelpersTests(TestCase):
    def test_budget_shows_real_currency_and_usd_estimate(self):
        self.assertEqual(budget_text(FEED[0]), '$250–750 USD')
        self.assertEqual(budget_text(FEED[3]), '₹12,500–37,500 INR (≈ $132–398)')
        hourly = project(9, 'x', [job('PHP', IT)], low=15, high=25, kind='hourly')
        self.assertEqual(budget_text(hourly), '$15–25/hr USD')

    def test_software_projects_only(self):
        self.assertTrue(is_software_project(FEED[0]))
        self.assertFalse(is_software_project(FEED[1]))   # design job with a stray PHP tag
        self.assertFalse(is_software_project(FEED[2]))   # marketing job
        self.assertTrue(is_software_project(FEED[3]))

    def test_search_query_uses_important_words(self):
        self.assertEqual(search_query('we need a mobile app developer'), 'app mobile')
        self.assertEqual(search_query('hiring react native developer'), 'react native')
        self.assertEqual(search_query('looking for a freelance developer'), '')


class FreelancerCollectionTests(TestCase):
    def setUp(self):
        self.web = Source.objects.create(name='Web search', connector_type='web_search', enabled=False)
        SearchTerm.objects.create(source=self.web, group_name='G', query='we need a mobile app developer')
        SearchTerm.objects.create(source=self.web, group_name='G', query='need someone to build my website')
        SearchTerm.objects.create(source=self.web, group_name='G', query='off keyword', enabled=False)
        self.source = Source.objects.get(connector_type='freelancer')  # created by migration

    def collect(self):
        from apps.sources.tasks import collect_source
        with mock.patch('httpx.Client.get', return_value=fake_response(FEED)) as get:
            counters = collect_source(str(self.source.id))
        return counters, get

    def test_uses_settings_keywords_and_keeps_only_matching_software_projects(self):
        counters, get = self.collect()
        queries = [call.kwargs['params'].get('query') for call in get.call_args_list]
        self.assertEqual(sorted(queries), ['app mobile', 'website'])

        leads = {o.requirement: o for o in Opportunity.objects.all()}
        self.assertEqual(set(leads), {'Build Flutter food delivery app', 'Restaurant website with booking'})
        app = leads['Build Flutter food delivery app']
        self.assertEqual((app.intent, app.kind, app.status), ('buyer', 'direct_purchase', 'new'))
        self.assertEqual(app.primary_category, 'MOBILE_APP')
        self.assertIn('Flutter', app.technology)
        self.assertTrue(app.source_url.startswith('https://www.freelancer.com/projects/'))
        self.assertEqual(leads['Restaurant website with booking'].budget_text, '₹12,500–37,500 INR (≈ $132–398)')
        self.assertEqual(counters['errors'], 0)

    def test_running_twice_does_not_duplicate_leads(self):
        self.collect()
        self.collect()
        self.assertEqual(Opportunity.objects.count(), 2)

    def test_switching_keyword_off_hides_its_freelancer_leads(self):
        from apps.sources.content_filters import refilter_existing_leads
        self.collect()
        SearchTerm.objects.filter(query='need someone to build my website').update(enabled=False)
        refilter_existing_leads()
        visible = set(Opportunity.objects.exclude(status='rejected').values_list('requirement', flat=True))
        self.assertEqual(visible, {'Build Flutter food delivery app'})

    def test_client_titles_like_hire_are_not_rejected_on_marketplace(self):
        from apps.sources.content_filters import lead_rejection_reason
        reason = lead_rejection_reason(
            title='Hire Flutter developer for my app', text='Need an iOS and Android mobile app. Skills: Flutter',
            url='https://www.freelancer.com/projects/flutter/Hire-Flutter-developer',
            ignore_keywords=['template'], search_keywords=['we need a mobile app developer'],
        )
        self.assertIsNone(reason)
