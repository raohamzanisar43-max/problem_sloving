"""Proposal studio: generate, score, save and mark a lead as proposal sent."""
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.opportunities.models import Draft, Opportunity
from apps.scoring.proposals import build_prompt, score_proposal

User = get_user_model()

GOOD = """Your food delivery app needs a smooth ordering flow for customers, a restaurant dashboard and live order tracking — that is exactly what we build.

How we would deliver it:
1. Confirm screens and the Stripe payment flow with you.
2. Build the Flutter app for iOS and Android with a Firebase backend.
3. Add the restaurant dashboard and live tracking with Google Maps.
4. Test on real devices and publish to both stores.

Do you already have designs, and should restaurants manage their own menus?

Happy to discuss on a quick call whenever suits you.

Novu Labs team"""


def make_opp(**kw):
    defaults = dict(
        requirement='Build Flutter food delivery app',
        text='We need a Flutter food delivery app with Stripe payments, a restaurant dashboard and '
             'live order tracking on Google Maps. Firebase backend preferred.',
        technology=['Flutter', 'Firebase', 'Stripe'], budget_text='$1,500–3,000 USD',
        intent='buyer', kind='direct_purchase', status='new', score=88, band='Hot',
        source_url='https://www.freelancer.com/projects/flutter/food-app',
    )
    defaults.update(kw)
    return Opportunity.objects.create(**defaults)


class ProposalQualityTests(TestCase):
    def test_specific_proposal_scores_high(self):
        result = score_proposal(GOOD, make_opp(), 'medium')
        self.assertGreaterEqual(result['score'], 80, result)

    def test_generic_proposal_scores_low_with_tips(self):
        generic = 'Dear Sir, I am interested in your project. I can do this job. [Your Name]'
        result = score_proposal(generic, make_opp(), 'medium')
        self.assertLess(result['score'], 30)
        tips = ' '.join(c['tip'] for c in result['checks'])
        self.assertIn('placeholders', tips)

    def test_prompt_contains_project_and_never_invents(self):
        system, user = build_prompt(make_opp(), 'friendly', 'short')
        self.assertIn('Stripe payments', user)
        self.assertIn('$1,500–3,000 USD', user)
        self.assertIn('70–130 words', user)
        self.assertIn('never invent', system)


class ProposalApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='exec', password='p', role='sales_executive')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.opp = make_opp()

    def test_generate_with_ai(self):
        with mock.patch('apps.scoring.proposals._chat', return_value=(GOOD, 'test-model')):
            resp = self.client.post(f'/api/v1/opportunities/{self.opp.id}/proposal/',
                                    {'tone': 'friendly', 'length': 'medium'}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertTrue(data['ai'])
        self.assertEqual(data['content'], GOOD)
        self.assertGreaterEqual(data['quality']['score'], 80)
        self.assertTrue(Draft.objects.filter(opportunity=self.opp, model_version__startswith='proposal:friendly/medium').exists())

        latest = self.client.get(f'/api/v1/opportunities/{self.opp.id}/proposal/latest/').json()
        self.assertEqual(latest['content'], GOOD)

    def test_without_ai_key_a_template_and_warning_are_returned(self):
        with mock.patch('apps.scoring.proposals._chat', side_effect=Exception('Error code: 401 - invalid_api_key')):
            data = self.client.post(f'/api/v1/opportunities/{self.opp.id}/proposal/', {}, format='json').json()
        self.assertFalse(data['ai'])
        self.assertIn('invalid or expired', data['warning'])
        self.assertIn('Build Flutter food delivery app', data['content'])

    def test_save_and_mark_applied(self):
        resp = self.client.post(f'/api/v1/opportunities/{self.opp.id}/proposal/save/',
                                {'content': GOOD + '\nEdited.', 'applied': True}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.status, 'proposal')
        self.assertEqual(self.opp.owner, self.user)
        self.assertEqual(resp.json()['opportunity']['status'], 'proposal')
        self.assertTrue(self.opp.activities.filter(action='status_change', to_value='proposal').exists())

    def test_live_score_endpoint_and_empty_save(self):
        score = self.client.post(f'/api/v1/opportunities/{self.opp.id}/proposal/score/',
                                 {'content': GOOD}, format='json').json()
        self.assertGreaterEqual(score['score'], 80)
        bad = self.client.post(f'/api/v1/opportunities/{self.opp.id}/proposal/save/', {'content': ' '}, format='json')
        self.assertEqual(bad.status_code, 400)
