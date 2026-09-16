"""
Manual capture (handover §4): paste a URL and a permitted excerpt, and the
evidence is stored and qualified the same way a collected row is.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.contacts.models import Contact
from apps.exports.models import OutboxEvent
from apps.observations.models import Observation
from apps.opportunities.models import Opportunity

User = get_user_model()


class FakeLLM:
    """Extraction result for a clearly-worded ERP request with a contact."""

    def __init__(self, **overrides):
        self.fields = {
            'requirement': 'ERP development partner for fleet operations',
            'intent': 'buyer',
            'kind': 'direct_purchase',
            'primary_category': 'ERP',
            'categories': ['ERP'],
            'technology': [],
            'company_name': 'Example Logistics',
            'company_domain': 'example.invalid',
            'country': 'PK',
            'industry': 'Logistics',
            'budget_text': '',
            'deadline': None,
            'email': 'procurement@example.invalid',
            'phone': '',
            'contact_name': 'Procurement Desk',
            'confidence': 0.92,
        }
        self.fields.update(overrides)

    def extract(self, text):
        return dict(self.fields)


class ManualCaptureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='e2', password='p', role='sales_executive')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.payload = {
            'url': 'https://example.invalid/post/1',
            'title': 'ERP partner needed',
            'text': 'We are a logistics firm and need an ERP development partner. '
                    'Write to procurement@example.invalid for the brief.',
            'company': 'Example Logistics',
        }

    def post(self, **overrides):
        body = dict(self.payload)
        body.update(overrides)
        return self.client.post('/api/v1/observations/', body, format='json')

    def test_capture_stores_evidence_and_creates_a_lead(self):
        with patch('apps.scoring.llm.LLMClient', return_value=FakeLLM()):
            resp = self.post()
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Observation.objects.count(), 1)
        self.assertEqual(Opportunity.objects.count(), 1)

        opportunity = Opportunity.objects.get()
        self.assertEqual(opportunity.primary_category, 'ERP')
        self.assertEqual(opportunity.source_url, self.payload['url'])
        self.assertEqual(resp.json()['opportunity']['id'], str(opportunity.id))

    def test_the_published_contact_is_stored_with_its_evidence(self):
        with patch('apps.scoring.llm.LLMClient', return_value=FakeLLM()):
            self.post()
        contact = Contact.objects.get()
        self.assertEqual(contact.email, 'procurement@example.invalid')
        self.assertEqual(contact.verification, 'published')
        self.assertEqual(contact.evidence_url, self.payload['url'])

    def test_capture_emits_an_outbox_event(self):
        with patch('apps.scoring.llm.LLMClient', return_value=FakeLLM()):
            self.post()
        self.assertTrue(OutboxEvent.objects.filter(destination='csv').exists())

    def test_low_confidence_extraction_is_held_for_review(self):
        with patch('apps.scoring.llm.LLMClient', return_value=FakeLLM(confidence=0.10)):
            self.post()
        opportunity = Opportunity.objects.get()
        self.assertEqual(opportunity.status, 'review')
        self.assertTrue(any('confidence' in r for r in opportunity.review_reasons))

    def test_seller_promotion_never_reaches_the_queue(self):
        with patch('apps.scoring.llm.LLMClient',
                   return_value=FakeLLM(intent='nonbuyer', kind='seller_promotion')):
            self.post()
        opportunity = Opportunity.objects.get()
        self.assertEqual(opportunity.status, 'rejected')
        self.assertEqual(opportunity.score, 0)

    def test_qualify_false_stores_evidence_only(self):
        with patch('apps.scoring.llm.LLMClient', return_value=FakeLLM()):
            resp = self.post(qualify=False)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Observation.objects.count(), 1)
        self.assertEqual(Opportunity.objects.count(), 0)
        self.assertIsNone(resp.json()['opportunity'])

    def test_text_is_required(self):
        resp = self.client.post('/api/v1/observations/', {'url': 'https://example.invalid/x'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_a_failed_extraction_still_keeps_the_evidence(self):
        class Exploding:
            def extract(self, text):
                raise RuntimeError('provider down')

        with patch('apps.scoring.llm.LLMClient', return_value=Exploding()):
            resp = self.post()
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Observation.objects.count(), 1)
        self.assertEqual(Opportunity.objects.count(), 0)
        self.assertIn('qualification_error', resp.json())
