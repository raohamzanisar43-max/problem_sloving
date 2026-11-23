"""Keywords written with search syntax (-excluded, OR, quotes) as on the live Settings screen."""
from django.test import SimpleTestCase

from apps.sources.collectors.freelancer import search_query
from apps.sources.content_filters import keyword_core, keyword_groups, matched_keyword

NEG = ' -jobs -hiring -vacancy -career -internship'


class KeywordSyntaxTests(SimpleTestCase):
    def test_excluded_words_are_not_required(self):
        self.assertEqual(keyword_core('need someone to build my website' + NEG), {'website'})
        self.assertEqual(
            matched_keyword(title='Need someone to build my bakery website', keywords=['need someone to build my website' + NEG]),
            'need someone to build my website' + NEG,
        )

    def test_quoted_keyword_with_exclusions(self):
        kw = '"need a python developer for my project"' + NEG
        self.assertTrue(matched_keyword(title='Python developer for a scraping script', keywords=[kw], marketplace=True))
        self.assertEqual(search_query(kw), 'python')

    def test_or_means_any_alternative(self):
        kw = '"website banwani hai" OR "website chahiye" OR "website banwana hai"'
        self.assertEqual(len(keyword_groups(kw)), 1)
        self.assertTrue(matched_keyword(text='Mujhe ek website chahiye apni shop ke liye', keywords=[kw]))
        kw2 = '"looking for a software house" OR "need a software company" Pakistan' + NEG
        self.assertTrue(matched_keyword(text='We need a software company in Pakistan for our ERP', keywords=[kw2]))
        self.assertFalse(matched_keyword(text='We need a software company in Dubai', keywords=[kw2]))

    def test_filler_alternative_makes_group_optional(self):
        kw = '"RFP" "mobile app development"' + NEG
        self.assertTrue(matched_keyword(text='RFP for mobile app development services', keywords=[kw]))

    def test_site_operator_ignored(self):
        self.assertEqual(keyword_core('need a shopify developer site:reddit.com'), {'shopify', 'developer'})

    def test_plain_keywords_unchanged(self):
        self.assertTrue(matched_keyword(title='Need a mobile app developer', keywords=['we need a mobile app developer']))
        self.assertFalse(matched_keyword(title='Need a logo', keywords=['we need a mobile app developer']))
        # Marketplace: role words are implied.
        self.assertTrue(matched_keyword(title='Mobile app for my gym', keywords=['need a mobile app developer'],
                                        marketplace=True))
