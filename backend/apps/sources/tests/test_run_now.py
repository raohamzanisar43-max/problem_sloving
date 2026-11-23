"""Source Health actions: run a source now, switch it on/off; recheck of keyword rejections."""
import importlib
from unittest import mock

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.opportunities.models import Opportunity
from apps.sources.models import Run, Source

User = get_user_model()


class RunNowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create_user(username='a', password='p', role='admin'))
        self.source = Source.objects.create(name='Reddit test', connector_type='reddit', enabled=True,
                                            access_state='ready')

    def test_run_now_starts_a_background_collection(self):
        with mock.patch('apps.sources.views.threading.Thread') as thread:
            resp = self.client.post(f'/api/v1/sources/{self.source.id}/run-now/')
        self.assertEqual(resp.status_code, 202)
        thread.return_value.start.assert_called_once()
        self.assertTrue(Run.objects.filter(source=self.source, trigger='manual').exists())
        with mock.patch('apps.sources.views.threading.Thread'):
            again = self.client.post(f'/api/v1/sources/{self.source.id}/run-now/')
        self.assertEqual(again.status_code, 409)

    def test_switched_off_source_cannot_run_and_toggle_works(self):
        resp = self.client.patch(f'/api/v1/sources/{self.source.id}/', {'enabled': False}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.post(f'/api/v1/sources/{self.source.id}/run-now/').status_code, 400)

    def test_sales_executive_cannot_run(self):
        exec_client = APIClient()
        exec_client.force_authenticate(User.objects.create_user(username='e', password='p', role='sales_executive'))
        self.assertEqual(exec_client.post(f'/api/v1/sources/{self.source.id}/run-now/').status_code, 403)


class RecheckMigrationTests(TestCase):
    def test_only_keyword_rejections_are_removed(self):
        stale = Opportunity.objects.create(
            requirement='Need a website', text='x', status='rejected',
            review_reasons=['Filtered out at collection: Does not match any search keyword'])
        other = Opportunity.objects.create(
            requirement='Agency blog', text='x', status='rejected',
            review_reasons=['Filtered out at collection: Ignore word: "guide"'])
        live = Opportunity.objects.create(requirement='Good lead', text='x', status='new')
        migration = importlib.import_module('apps.sources.migrations.0004_recheck_keyword_rejections')
        migration.recheck(django_apps, None)
        self.assertFalse(Opportunity.objects.filter(pk=stale.pk).exists())
        self.assertTrue(Opportunity.objects.filter(pk=other.pk).exists())
        self.assertTrue(Opportunity.objects.filter(pk=live.pk).exists())
