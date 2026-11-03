from datetime import datetime, timedelta, timezone as dt_tz
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.sources.collectors.brave import MARKET_COUNTRY, _parse_age
from apps.sources.management.commands.seed_search_terms import TERMS
from apps.sources.models import SearchTerm, Source


class SeedSearchTermsTests(TestCase):
    def setUp(self):
        self.source = Source.objects.create(
            name='Brave web search', connector_type='web_search', enabled=True, access_state='ready',
        )

    def test_loads_terms_for_both_markets_and_is_idempotent(self):
        call_command('seed_search_terms', stdout=StringIO())
        call_command('seed_search_terms', stdout=StringIO())
        self.assertEqual(SearchTerm.objects.filter(source=self.source).count(), len(TERMS))
        markets = set(SearchTerm.objects.values_list('market', flat=True))
        self.assertEqual(markets, {'PK', 'WORLD'})

    def test_replace_disables_other_terms(self):
        old = SearchTerm.objects.create(source=self.source, group_name='Old', query='old query')
        call_command('seed_search_terms', '--replace', stdout=StringIO())
        old.refresh_from_db()
        self.assertFalse(old.enabled)

    def test_hiring_posts_are_excluded_in_english_queries(self):
        english = [q for _, _, q in TERMS if 'chahiye' not in q and 'banwa' not in q]
        self.assertTrue(all('-jobs' in q and '-hiring' in q for q in english))


class BraveAgeTests(TestCase):
    def test_iso_page_age(self):
        self.assertEqual(_parse_age('2026-10-22T15:37:37'), datetime(2026, 10, 22, 15, 37, 37, tzinfo=dt_tz.utc))

    def test_relative_age(self):
        parsed = _parse_age('2 weeks ago')
        self.assertAlmostEqual((datetime.now(dt_tz.utc) - parsed).days, 14, delta=1)

    def test_garbage_age_is_none(self):
        self.assertIsNone(_parse_age('sometime'))
        self.assertIsNone(_parse_age(None))

    def test_pakistan_is_not_sent_as_a_brave_country(self):
        self.assertNotIn('PK', MARKET_COUNTRY)


class ExtractionInputTests(TestCase):
    def test_model_sees_title_and_url_with_the_snippet(self):
        from types import SimpleNamespace
        from apps.sources.tasks import extraction_input
        obs = SimpleNamespace(title='RFP: website redesign', original_url='https://example.org/rfp', text='We seek a vendor.')
        out = extraction_input(obs)
        self.assertIn('RFP: website redesign', out)
        self.assertIn('https://example.org/rfp', out)
        self.assertTrue(out.endswith('We seek a vendor.'))


class ContentPageFilterTests(TestCase):
    def _obs(self, title, url='https://example.org/x'):
        from types import SimpleNamespace
        return SimpleNamespace(title=title, original_url=url, text='')

    def test_listicles_guides_templates_and_directories_are_filtered(self):
        from apps.sources.tasks import is_content_page
        for title in (
            'Top 12 Scalable Web Development Companies for SMEs in Pakistan',
            'Best Healthcare VMS Companies in 2026',
            'How to Choose an AI Automation Agency',
            'ERP Implementation Proposal Template for Projects',
            'Website Redesign RFP Example',
            'Top Mobile App Development Companies in Punjab',
        ):
            self.assertTrue(is_content_page(self._obs(title)), title)
        self.assertTrue(is_content_page(self._obs('Anything', 'https://www.clutch.co/profile/x')))

    def test_real_requests_are_not_filtered(self):
        from apps.sources.tasks import is_content_page
        for title in (
            'RFP: Website Redesign and Hosting Services',
            'Request for Proposals - Website Management',
            'Need ecommerce website built for my bakery in Karachi',
            'Tender for development of web portal',
        ):
            self.assertFalse(is_content_page(self._obs(title)), title)


class ExtractionUnavailableTests(TestCase):
    def test_quota_failure_defers_instead_of_saving_a_stub_lead(self):
        from datetime import datetime, timezone as tz
        from unittest.mock import patch
        from apps.observations.models import Observation
        from apps.opportunities.models import Opportunity
        from apps.scoring.llm import ExtractionUnavailable
        from apps.sources.tasks import collect_source

        source = Source.objects.create(name='Web', connector_type='web_search', enabled=True)
        Observation.objects.create(
            source=source, external_id='1', title='Need a website built', text='We need a website built for our clinic.',
            original_url='https://example.org/1', source_published_at=datetime(2026, 11, 1, tzinfo=tz.utc),
        )

        class Broken:
            def extract(self, text):
                raise ExtractionUnavailable('429 quota')

        with patch('apps.sources.tasks._import_collector') as imp, patch('apps.scoring.llm.LLMClient', return_value=Broken()):
            imp.return_value = lambda src: type('C', (), {'run': lambda self, run, terms: (0, 0, 0, [])})()
            counters = collect_source(str(source.id))

        self.assertEqual(Opportunity.objects.count(), 0)
        self.assertEqual(counters['deferred'], 1)


class ClientKeywordTests(TestCase):
    def test_every_client_phrase_is_searched_verbatim_as_keywords(self):
        from apps.sources.management.commands.seed_search_terms import CLIENT_KEYWORDS
        queries = {q for _, _, q in TERMS}
        for phrases in CLIENT_KEYWORDS.values():
            for phrase in phrases:
                # Unquoted: Brave returns almost nothing for these as exact phrases.
                self.assertTrue(any(q.startswith(f'{phrase} -jobs') for q in queries), phrase)

    def test_client_groups_are_preserved(self):
        groups = {g for g, _, _ in TERMS}
        for name in ('Accounting & tax services', 'AML & compliance services', 'Governance & audit services'):
            self.assertIn(name, groups)


class AdvisoryCategoryTests(TestCase):
    def test_advisory_categories_count_as_a_service_match(self):
        from apps.scoring.engine import score_service_match
        for category in ('COMPLIANCE_AML', 'ACCOUNTING_TAX', 'GOVERNANCE_AUDIT'):
            self.assertEqual(score_service_match([category]), 25, category)

    def test_prompt_lists_the_advisory_categories(self):
        from apps.scoring.llm import extraction_system_prompt
        prompt = extraction_system_prompt()
        for category in ('COMPLIANCE_AML', 'ACCOUNTING_TAX', 'GOVERNANCE_AUDIT'):
            self.assertIn(category, prompt)


class ScoringOrderTests(TestCase):
    def test_freshest_posts_are_scored_first(self):
        from datetime import datetime, timezone as tz
        from unittest.mock import patch
        from apps.observations.models import Observation
        from apps.sources.tasks import collect_source

        source = Source.objects.create(name='Web', connector_type='web_search', enabled=True)
        for ext, day in (('old', 1), ('new', 20), ('mid', 10)):
            Observation.objects.create(
                source=source, external_id=ext, title=f'Need a website {ext}', text='We need a website built.',
                original_url=f'https://example.org/{ext}', source_published_at=datetime(2026, 10, day, tzinfo=tz.utc),
            )
        seen = []

        class Recorder:
            def extract(self, text):
                seen.append(text)
                return {'intent': 'nonbuyer', 'kind': 'other', 'confidence': 1.0}

        with patch('apps.sources.tasks._import_collector') as imp, patch('apps.scoring.llm.LLMClient', return_value=Recorder()):
            imp.return_value = lambda src: type('C', (), {'run': lambda self, run, terms: (0, 0, 0, [])})()
            collect_source(str(source.id))

        self.assertEqual([t.split('\n')[0] for t in seen], ['Title: Need a website new', 'Title: Need a website mid', 'Title: Need a website old'])
