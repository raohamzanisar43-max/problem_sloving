"""
CSV safety and outbox idempotency (handover §9, §12).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.exports.csv_utils import build_csv, safe_cell
from apps.exports.models import OutboxEvent
from apps.exports.outbox import emit, emit_for_opportunity
from apps.opportunities.models import Opportunity

User = get_user_model()


class FormulaInjectionTests(TestCase):
    def test_dangerous_prefixes_are_neutralised(self):
        for payload in ('=cmd|calc', '+1+1', '-1+1', '@SUM(A1)', '\t=1+1', '  =HYPERLINK("x")'):
            with self.subTest(payload=payload):
                self.assertTrue(safe_cell(payload).startswith("'"))

    def test_ordinary_text_is_untouched(self):
        for payload in ('ERP partner needed', 'buyer@example.invalid', '100'):
            with self.subTest(payload=payload):
                self.assertEqual(safe_cell(payload), payload)

    def test_none_becomes_blank(self):
        self.assertEqual(safe_cell(None), '')

    def test_injected_requirement_is_neutralised_in_the_file(self):
        Opportunity.objects.create(requirement='=1+1', status='new', score=10)
        body = build_csv(Opportunity.objects.all()).decode('utf-8')
        self.assertIn("'=1+1", body)
        self.assertTrue(body.startswith('﻿'), 'Excel needs the UTF-8 BOM')


class OutboxTests(TestCase):
    def setUp(self):
        self.opportunity = Opportunity.objects.create(
            requirement='ERP partner needed', status='new', score=90, band='Hot',
        )

    def test_emit_is_idempotent_for_a_revision(self):
        self.assertIsNotNone(emit('csv', self.opportunity))
        self.assertIsNone(emit('csv', self.opportunity))
        self.assertEqual(OutboxEvent.objects.filter(destination='csv').count(), 1)

    def test_a_new_revision_emits_a_new_event(self):
        emit('csv', self.opportunity)
        self.opportunity.revision += 1
        self.opportunity.save(update_fields=['revision'])
        self.assertIsNotNone(emit('csv', self.opportunity))
        self.assertEqual(OutboxEvent.objects.filter(destination='csv').count(), 2)

    def test_event_key_encodes_destination_opportunity_and_revision(self):
        event = emit('csv', self.opportunity)
        self.assertEqual(event.event_key, f'csv:{self.opportunity.id}:{self.opportunity.revision}')

    def test_alerting_is_off_without_a_recipient(self):
        emit_for_opportunity(self.opportunity)
        self.assertFalse(OutboxEvent.objects.filter(destination='email').exists())

    def test_high_score_alerts_when_a_recipient_is_configured(self):
        from apps.core.models import AppSetting
        AppSetting.objects.create(key='alert_email', value='sales@example.invalid')
        emit_for_opportunity(self.opportunity)
        self.assertTrue(OutboxEvent.objects.filter(destination='email').exists())

    def test_low_score_does_not_alert(self):
        from apps.core.models import AppSetting
        AppSetting.objects.create(key='alert_email', value='sales@example.invalid')
        low = Opportunity.objects.create(requirement='Maybe', status='new', score=20)
        emit_for_opportunity(low)
        self.assertFalse(OutboxEvent.objects.filter(destination='email', opportunity_id=low.id).exists())


class StatusChangeEmitsOutboxTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username='m3', password='p', role='sales_manager')
        self.client = APIClient()
        self.client.force_authenticate(self.manager)
        self.opportunity = Opportunity.objects.create(
            requirement='ERP partner needed', status='new', score=90, band='Hot',
        )

    def test_status_change_records_an_outbox_event(self):
        resp = self.client.patch(
            f'/api/v1/opportunities/{self.opportunity.id}/',
            {'status': 'reviewed', 'expected_revision': self.opportunity.revision},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(OutboxEvent.objects.filter(opportunity_id=self.opportunity.id).exists())

    def test_a_no_op_patch_emits_nothing(self):
        self.client.patch(
            f'/api/v1/opportunities/{self.opportunity.id}/',
            {'status': 'new', 'expected_revision': self.opportunity.revision},
            format='json',
        )
        self.assertEqual(OutboxEvent.objects.count(), 0)

    def test_revision_conflict_is_rejected(self):
        resp = self.client.patch(
            f'/api/v1/opportunities/{self.opportunity.id}/',
            {'status': 'reviewed', 'expected_revision': 99},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)


class SyncJobTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username='m4', password='p', role='sales_manager')
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def test_sync_reports_skipped_when_graph_is_not_configured(self):
        resp = self.client.post('/api/v1/sync/jobs/', {}, format='json')
        self.assertEqual(resp.status_code, 202)
        body = resp.json()
        self.assertEqual(body['state'], 'skipped')
        self.assertIn('MS_GRAPH_CLIENT_ID', body['error'])
