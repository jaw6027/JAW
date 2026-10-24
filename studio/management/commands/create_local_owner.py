import secrets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Development only: create an owner and store generated login details privately in data/.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('For production, use createsuperuser instead.')
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write('An owner already exists; no account changed.')
            return
        password = secrets.token_urlsafe(24)
        User.objects.create_superuser('owner', password=password)
        path = settings.DATA_DIR / 'local-owner-access.txt'
        path.write_text(f'Local development owner only\nLogin: /owner/\nUsername: owner\nPassword: {password}\nKeep this file private. Change the password before launch.\n')
        path.chmod(0o600)
        self.stdout.write(f'Local owner created. Read your private login details in {path}. No password printed to logs.')
