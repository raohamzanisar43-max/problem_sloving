"""
Operating settings: the Settings screen reflects what the deployment is really
running, and only administrators can change the tunable values.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import AppSetting
from apps.core.operating_settings import get_setting

User = get_user_model()


class OperatingSettingsApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='a3', password='p', role='admin')
        self.executive = User.objects.create_user(username='e3', password='p', role='sales_executive')

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_health_is_public(self):
        self.assertEqual(APIClient().get('/api/v1/health/').status_code, 200)

    def test_settings_require_authentication(self):
        self.assertEqual(APIClient().get('/api/v1/settings/').status_code, 401)

    def test_any_sales_role_can_read_settings(self):
        resp = self.client_for(self.executive).get('/api/v1/settings/')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body['editable'])
        keys = {item['key'] for item in body['settings']}
        self.assertIn('qualification_confidence', keys)
        self.assertIn('llm_provider', keys)

    def test_executives_cannot_change_settings(self):
        resp = self.client_for(self.executive).patch(
            '/api/v1/settings/', {'alert_min_score': 10}, format='json',
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_change_an_editable_setting(self):
        resp = self.client_for(self.admin).patch(
            '/api/v1/settings/', {'qualification_confidence': 0.5}, format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(get_setting('qualification_confidence'), 0.5)
        self.assertEqual(AppSetting.objects.get(pk='qualification_confidence').updated_by, self.admin)

    def test_out_of_range_values_are_rejected(self):
        resp = self.client_for(self.admin).patch(
            '/api/v1/settings/', {'alert_min_score': 500}, format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('alert_min_score', resp.json()['errors'])
        self.assertFalse(AppSetting.objects.filter(pk='alert_min_score').exists())

    def test_environment_owned_settings_cannot_be_edited(self):
        resp = self.client_for(self.admin).patch(
            '/api/v1/settings/', {'llm_provider': 'openai'}, format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_unknown_keys_are_rejected(self):
        resp = self.client_for(self.admin).patch(
            '/api/v1/settings/', {'not_a_setting': 1}, format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_credentials_are_never_exposed(self):
        body = self.client_for(self.admin).get('/api/v1/settings/').json()
        serialised = str(body).lower()
        for secret in ('api_key', 'client_secret', 'bearer', 'password'):
            self.assertNotIn(secret, serialised)

    def test_provider_reports_degradation(self):
        body = self.client_for(self.admin).get('/api/v1/settings/').json()
        self.assertEqual(body['provider']['active'], 'stub')
        self.assertFalse(body['provider']['degraded'])


class SettingResolutionTests(TestCase):
    def test_database_value_overrides_the_environment_default(self):
        default = get_setting('alert_min_score')
        AppSetting.objects.create(key='alert_min_score', value=42)
        self.assertEqual(get_setting('alert_min_score'), 42)
        self.assertNotEqual(get_setting('alert_min_score'), default)

    def test_read_only_settings_ignore_database_rows(self):
        AppSetting.objects.create(key='llm_provider', value='openai')
        self.assertEqual(get_setting('llm_provider'), 'stub')
