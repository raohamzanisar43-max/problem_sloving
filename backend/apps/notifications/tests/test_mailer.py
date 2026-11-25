"""Reply alert emails: nothing on proposals; optional email when a client replies."""
from email.message import EmailMessage as ParsedEmail

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.notifications.inbox import process_message
from apps.notifications.mailer import ALERT_HEADER
from apps.notifications.models import Notification
from apps.opportunities.models import Activity, Opportunity

User = get_user_model()


@override_settings(TEAM_ALERT_EMAILS=['info@novulabs.net'], APP_BASE_URL='https://radar.test')
class TeamAlertEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='exec', password='p', role='sales_executive')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.lead = Opportunity.objects.create(
            requirement='Build Flutter food delivery app', text='...', status='new',
            budget_text='$1,500–3,000 USD', source_url='https://www.freelancer.com/projects/flutter/food-app',
        )
        Activity.objects.create(opportunity=self.lead, action='status_change', from_value='new',
                                to_value='proposal', payload={'via': 'proposal_studio'})

    def test_marking_proposal_sent_sends_no_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(f'/api/v1/opportunities/{self.lead.id}/proposal/save/',
                                    {'content': 'Hello, our proposal text.', 'applied': True}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(TEAM_ALERT_EMAILS=[])
    def test_reply_alert_email_is_off_by_default(self):
        self.lead.status = 'proposal'
        self.lead.save()
        msg = ParsedEmail()
        msg['Subject'] = 'Re: Build Flutter food delivery app'
        msg['From'] = 'sara@client.com'
        msg['Message-ID'] = '<r0@client.com>'
        msg.set_content('Interested.')
        with self.captureOnCommitCallbacks(execute=True):
            created = process_message(msg)
        self.assertEqual(len(created), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_client_reply_emails_the_team_once(self):
        self.lead.status = 'proposal'
        self.lead.save()
        msg = ParsedEmail()
        msg['Subject'] = 'Re: Build Flutter food delivery app'
        msg['From'] = 'Sara <sara@client.com>'
        msg['Message-ID'] = '<r1@client.com>'
        msg.set_content('Yes, let us talk on Monday.')
        with self.captureOnCommitCallbacks(execute=True):
            process_message(msg)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Client replied: Build Flutter food delivery app', mail.outbox[0].subject)
        self.assertIn('let us talk on Monday', mail.outbox[0].body)
        self.assertIn('sara@client.com', mail.outbox[0].body)

    def test_our_own_alert_email_is_never_treated_as_a_reply(self):
        self.lead.status = 'proposal'
        self.lead.save()
        msg = ParsedEmail()
        msg['Subject'] = 'Proposal sent: Build Flutter food delivery app'
        msg['From'] = 'NovuRadar <alerts@other-box.com>'
        msg['Message-ID'] = '<a1@novulabs.net>'
        msg[ALERT_HEADER] = '1'
        msg.set_content('Project: Build Flutter food delivery app')
        self.assertEqual(process_message(msg), [])
        self.assertEqual(Notification.objects.count(), 0)
