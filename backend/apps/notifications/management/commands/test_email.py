from django.conf import settings
from django.core.management.base import BaseCommand

from apps.notifications.mailer import _send, is_configured


class Command(BaseCommand):
    help = 'Send a test email from the reply mailbox to itself, to check the mail settings.'

    def handle(self, *args, **options):
        if not is_configured():
            self.stdout.write(self.style.WARNING(
                'EMAIL_HOST_USER / EMAIL_HOST_PASSWORD are empty in backend/.env, so the email is only '
                'printed below instead of being sent.'))
        recipients = settings.TEAM_ALERT_EMAILS or [settings.EMAIL_HOST_USER or 'info@novulabs.net']
        _send('NovuRadar test email',
              'If you can read this, NovuRadar can use this mailbox. Client replies to proposals will '
              'show up as notifications in NovuRadar.', recipients)
        self.stdout.write(self.style.SUCCESS(
            f"Done. Sent from {settings.DEFAULT_FROM_EMAIL} to {', '.join(recipients)} "
            f"via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}."))
