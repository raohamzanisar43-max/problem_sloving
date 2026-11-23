from django.conf import settings
from django.core.management.base import BaseCommand

from apps.notifications.mailer import is_configured, send_team_email


class Command(BaseCommand):
    help = 'Send a test alert email to TEAM_ALERT_EMAILS (info@novulabs.net) to check the mail settings.'

    def handle(self, *args, **options):
        if not is_configured():
            self.stdout.write(self.style.WARNING(
                'EMAIL_HOST_USER / EMAIL_HOST_PASSWORD are empty in backend/.env, so the email is only '
                'printed below instead of being sent.'))
        send_team_email(
            'NovuRadar test email',
            'If you can read this in the inbox, NovuRadar alert emails are working.\n\n'
            'You will get an email here whenever a proposal is marked as sent and whenever a client replies.',
            background=False,
        )
        self.stdout.write(self.style.SUCCESS(
            f"Done. Sent from {settings.DEFAULT_FROM_EMAIL} to {', '.join(settings.TEAM_ALERT_EMAILS)} "
            f"via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}. Check the inbox (and spam)."))
