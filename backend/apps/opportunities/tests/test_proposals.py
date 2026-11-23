"""Proposal studio: generate, score, save and mark a lead as proposal sent."""
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.opportunities.models import Draft, Opportunity
from apps.scoring.proposals import build_prompt, finalize, score_proposal, signature

User = get_user_model()

# What the model returns: the body only (the signature is added by code).
AI_BODY = """Hello,

NovuLabs is an enterprise software house in Islamabad, and food delivery apps with live tracking and online payments are exactly the kind of product we build.

Our understanding:
You need a Flutter food delivery app for iOS and Android with a smooth ordering flow for customers, Stripe payments, a restaurant dashboard to manage menus and incoming orders, and live order tracking on Google Maps, all running on a Firebase backend. The app must stay fast during peak hours and keep restaurants, riders and customers in sync in real time.

Proposed approach:
1. Discovery: confirm the screens, user roles and the Stripe payment flow with you, and agree on milestones.
2. Backend: set up Firebase authentication, Firestore data models for menus and orders, and Cloud Functions for order events.
3. Customer app: build the Flutter app with browsing, cart, Stripe checkout and push notifications.
4. Restaurant dashboard: a web dashboard where restaurants manage menus, accept orders and update their status.
5. Live tracking: Google Maps tracking of the rider with estimated arrival times.
6. Testing and launch: test on real devices, then publish to the App Store and Google Play.

Relevant experience:
We built and run live multi-role platforms such as NovuLabs EduCore and MarketingOS, with separate portals, approvals and real-time updates.

What you can expect:
Milestones with working demos, an NDA signed upfront, direct contact with the engineer building your app, and post-launch support.

Do you already have designs for the screens, and should restaurants manage their own menus and opening hours?

We would be happy to discuss the details on a short call whenever suits you."""

GOOD = finalize(AI_BODY)


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
        self.assertGreaterEqual(result['score'], 85, result)

    def test_generic_proposal_scores_low_with_tips(self):
        generic = 'Dear Sir, I am interested in your project. I can do this job. [Your Name]'
        result = score_proposal(generic, make_opp(), 'medium')
        self.assertLess(result['score'], 30)
        tips = ' '.join(c['tip'] for c in result['checks'])
        self.assertIn('placeholders', tips)
        self.assertIn('info@novulabs.net', tips)

    def test_prompt_contains_project_company_and_never_invents(self):
        system, user = build_prompt(make_opp(), 'professional', 'long')
        self.assertIn('Stripe payments', user)
        self.assertIn('$1,500–3,000 USD', user)
        self.assertIn('380–520 words', user)
        self.assertIn('NovuLabs EduCore', user)
        self.assertIn('never invent', system)
        self.assertIn('signature is added automatically', system)

    def test_finalize_adds_intro_and_one_signature(self):
        text = finalize('Hello,\n\nYour app needs X.\n\nBest regards,\nJohn')
        self.assertIn('NovuLabs is an enterprise software house', text)
        self.assertTrue(text.endswith(signature(True)))
        self.assertNotIn('John', text)
        self.assertEqual(text.count('Best regards'), 1)
        self.assertIn('info@novulabs.net', text)
        self.assertIn('+92 326 8292154', text)

    def test_signature_without_contact(self):
        text = finalize(AI_BODY, include_contact=False)
        self.assertNotIn('info@novulabs.net', text)
        self.assertTrue(text.endswith('NovuLabs Team'))


class ProposalApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='exec', password='p', role='sales_executive')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.opp = make_opp()

    def test_generate_with_ai(self):
        with mock.patch('apps.scoring.proposals._chat', return_value=(AI_BODY, 'test-model')):
            resp = self.client.post(f'/api/v1/opportunities/{self.opp.id}/proposal/',
                                    {'tone': 'friendly', 'length': 'medium'}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertTrue(data['ai'])
        self.assertEqual(data['content'], GOOD)
        self.assertIn('info@novulabs.net', data['content'])
        self.assertTrue(data['notice'])  # Freelancer.com: contact details warning
        self.assertGreaterEqual(data['quality']['score'], 85)
        self.assertTrue(Draft.objects.filter(opportunity=self.opp, model_version__startswith='proposal:friendly/medium').exists())

        latest = self.client.get(f'/api/v1/opportunities/{self.opp.id}/proposal/latest/').json()
        self.assertEqual(latest['content'], GOOD)

    def test_generate_without_contact_details(self):
        with mock.patch('apps.scoring.proposals._chat', return_value=(AI_BODY, 'test-model')):
            data = self.client.post(f'/api/v1/opportunities/{self.opp.id}/proposal/',
                                    {'include_contact': False}, format='json').json()
        self.assertNotIn('info@novulabs.net', data['content'])
        self.assertEqual(data['notice'], '')

    def test_without_ai_key_a_template_and_warning_are_returned(self):
        with mock.patch('apps.scoring.proposals._chat', side_effect=Exception('Error code: 401 - invalid_api_key')):
            data = self.client.post(f'/api/v1/opportunities/{self.opp.id}/proposal/', {}, format='json').json()
        self.assertFalse(data['ai'])
        self.assertIn('invalid or expired', data['warning'])
        self.assertIn('Build Flutter food delivery app', data['content'])
        self.assertIn('NovuLabs', data['content'])
        self.assertIn('info@novulabs.net', data['content'])

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
        self.assertGreaterEqual(score['score'], 85)
        bad = self.client.post(f'/api/v1/opportunities/{self.opp.id}/proposal/save/', {'content': ' '}, format='json')
        self.assertEqual(bad.status_code, 400)
