import fcntl
from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from studio.models import Notification, SiteSettings
from studio.emailing import DeliveryError, send_email, notification_content


class Command(BaseCommand):
    help = 'Deliver queued emails with provider idempotency and a single-worker lock.'

    def handle(self, *args, **options):
        if not settings.EMAIL_READY:
            raise CommandError('Preview mode: RESEND_API_KEY and EMAIL_FROM are required. No emails sent.')
        with open(settings.DATA_DIR / '.email-worker.lock', 'w') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self.stdout.write('Another worker is running; nothing sent.')
                return
            for note in Notification.objects.filter(sent_at__isnull=True, blocked=False).select_related('design', 'subscriber'):
                if not note.subscriber.active or not note.subscriber.confirmed_at or note.design.status != 'published':
                    continue
                # Resend retains idempotency keys for 24 hours. Never automatically
                # retry an ambiguous request after that window: duplicates matter.
                if note.attempted_at and note.attempted_at < timezone.now() - timedelta(hours=23):
                    note.blocked = True
                    note.last_error = 'Retry window expired. Check provider logs before manual reconciliation.'
                    note.save(update_fields=['blocked', 'last_error'])
                    continue
                if not note.attempted_at:
                    note.attempted_at = timezone.now()
                    note.subject_snapshot = f'{SiteSettings.load().brand_name}: {note.design.title}'[:250]
                    note.html_snapshot = notification_content(note)
                    note.save(update_fields=['attempted_at', 'subject_snapshot', 'html_snapshot'])
                try:
                    send_email(note.subscriber.email, note.subject_snapshot, note.html_snapshot, f'design-{note.design_id}-subscriber-{note.subscriber_id}')
                except DeliveryError as exc:
                    note.last_error = str(exc)[:200]
                    note.save(update_fields=['last_error'])
                    self.stderr.write(f'Notification {note.pk}: provider acceptance not confirmed.')
                else:
                    note.sent_at = timezone.now()
                    note.last_error = ''
                    note.save(update_fields=['sent_at', 'last_error'])
                    self.stdout.write(f'Notification {note.pk}: accepted by provider.')
