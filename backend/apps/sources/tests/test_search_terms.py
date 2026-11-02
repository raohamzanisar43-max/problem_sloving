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
