from django.conf import settings
from .models import SiteSettings


def brand(request):
    return {'brand': SiteSettings.load(), 'email_ready': settings.EMAIL_READY, 'site_url': settings.SITE_URL}
