from django.core.management.base import BaseCommand

from apps.notifications.inbox import check_inbox


class Command(BaseCommand):
    help = 'Read new email from the reply inbox and notify the team about client replies.'

    def handle(self, *args, **options):
        result = check_inbox()
        if not result.get('configured'):
            self.stdout.write(self.style.WARNING(
                'Reply inbox not configured: set INBOX_IMAP_HOST, INBOX_EMAIL and INBOX_PASSWORD in .env.'))
            return
        if not result.get('ok'):
            self.stdout.write(self.style.ERROR(f"Inbox check failed: {result.get('error')}"))
            return
        self.stdout.write(self.style.SUCCESS(
            f"Scanned {result['scanned']} email(s), {result['notified']} new notification(s)."))
