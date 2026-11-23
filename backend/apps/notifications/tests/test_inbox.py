"""Reply inbox: matching client emails to leads and the notifications API."""
from email.message import EmailMessage
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.notifications.inbox import check_inbox, process_message
from apps.notifications.models import InboxMessage, Notification
from apps.opportunities.models import Opportunity

User = get_user_model()


def mail(subject, body, sender='Client <client@acme.com>', msg_id='<1@acme.com>'):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = 'info@novulabs.net'
    msg['Message-ID'] = msg_id
    msg['Date'] = 'Mon, 23 Nov 2026 10:00:00 +0000'
    msg.set_content(body)
    return msg


class InboxMatchingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='p', role='sales_executive')
        self.other = User.objects.create_user(username='other', password='p', role='sales_manager')
        self.lead = Opportunity.objects.create(
            requirement='Build Flutter food delivery app', text='...', status='proposal', owner=self.owner,
            source_url='https://www.freelancer.com/projects/flutter/build-flutter-food-delivery-app',
        )

    def test_reply_matched_by_title_notifies_owner_and_logs_activity(self):
        created = process_message(mail('Re: Build Flutter food delivery app', 'Sounds good, can we talk tomorrow?'))
        self.assertEqual(len(created), 1)
        n = created[0]
        self.assertEqual(n.recipient, self.owner)
        self.assertEqual(n.opportunity, self.lead)
        self.assertIn('can we talk tomorrow', n.body)
        self.assertTrue(self.lead.activities.filter(action='client_reply').exists())

    def test_freelancer_alert_matched_by_project_link(self):
        body = ('John sent you a message about your bid.\n'
                'https://www.freelancer.com/projects/flutter/build-flutter-food-delivery-app/details')
        created = process_message(mail('You have a new message', body,
                                       sender='Freelancer <noreply@notifications.freelancer.com>'))
        self.assertEqual(created[0].kind, 'marketplace_message')
        self.assertEqual(created[0].opportunity, self.lead)

    def test_same_email_is_processed_once(self):
        msg = mail('Re: Build Flutter food delivery app', 'Yes')
        process_message(msg)
        self.assertEqual(process_message(msg), [])
        self.assertEqual(Notification.objects.count(), 1)

    def test_unrelated_email_is_ignored(self):
        self.assertEqual(process_message(mail('Newsletter', 'Big sale this week', msg_id='<2@x>')), [])
        self.assertTrue(InboxMessage.objects.filter(message_id='<2@x>', notified=False).exists())

    def test_reply_to_our_proposal_without_lead_notifies_everyone(self):
        body = 'Interested, please call.\n\n> Best regards,\n> NovuLabs Team\n> info@novulabs.net'
        created = process_message(mail('Re: Your proposal', body, msg_id='<3@x>'))
        self.assertEqual({n.recipient for n in created}, {self.owner, self.other})
        self.assertIsNone(created[0].opportunity)

    def test_unconfigured_inbox_does_nothing(self):
        self.assertEqual(check_inbox()['configured'], False)


class NotificationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='p', role='sales_executive')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        Notification.objects.create(recipient=self.user, title='Reply on: A', body='hi')
        Notification.objects.create(recipient=self.user, title='Reply on: B', body='hello')

    def test_list_count_and_mark_read(self):
        self.assertEqual(self.client.get('/api/v1/notifications/unread-count/').json()['count'], 2)
        items = self.client.get('/api/v1/notifications/').json()
        self.assertEqual(len(items), 2)
        self.client.post(f"/api/v1/notifications/{items[0]['id']}/read/")
        self.assertEqual(self.client.get('/api/v1/notifications/unread-count/').json()['count'], 1)
        self.client.post('/api/v1/notifications/read-all/')
        self.assertEqual(self.client.get('/api/v1/notifications/unread-count/').json()['count'], 0)

    def test_inbox_status_and_check_when_not_configured(self):
        self.assertFalse(self.client.get('/api/v1/notifications/inbox-status/').json()['configured'])
        self.assertEqual(self.client.post('/api/v1/notifications/check-inbox/').status_code, 400)

    @override_settings(INBOX={'HOST': 'imap.example.com', 'PORT': 993, 'USER': 'info@novulabs.net',
                              'PASSWORD': 'x', 'FOLDER': 'INBOX', 'LOOKBACK_DAYS': 3, 'CHECK_MINUTES': 5})
    def test_login_failure_is_reported(self):
        import imaplib
        with mock.patch('imaplib.IMAP4_SSL') as imap:
            imap.return_value.login.side_effect = imaplib.IMAP4.error('[AUTHENTICATIONFAILED] Invalid credentials')
            status = self.client.post('/api/v1/notifications/check-inbox/').json()
        self.assertFalse(status['last_ok'])
        self.assertIn('App Password', status['last_error'])
