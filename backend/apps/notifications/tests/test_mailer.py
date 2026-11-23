"""Team alert emails to info@novulabs.net: proposal sent and client replied."""
from email.message import EmailMessage as ParsedEmail

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.notifications.inbox import process_message
from apps.notifications.mailer import ALERT_HEADER
from apps.notifications.models import Notification
from apps.opportunities.models import Opportunity

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

    def test_marking_proposal_sent_emails_a_copy(self):
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(f'/api/v1/opportunities/{self.lead.id}/proposal/save/',
                                    {'content': 'Hello, our proposal text.', 'applied': True}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['info@novulabs.net'])
        self.assertIn('Proposal sent: Build Flutter food delivery app', sent.subject)
        self.assertIn('Hello, our proposal text.', sent.body)
        self.assertIn('$1,500–3,000 USD', sent.body)
        self.assertIn(f'https://radar.test/lead/{self.lead.id}', sent.body)
        self.assertEqual(sent.extra_headers.get(ALERT_HEADER), '1')

    def test_saving_a_draft_without_applying_sends_nothing(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(f'/api/v1/opportunities/{self.lead.id}/proposal/save/',
                             {'content': 'Draft only'}, format='json')
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
