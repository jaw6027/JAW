"""Resend integration. Never reports preview messages as delivered."""
import json
from html import escape
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from django.conf import settings
from django.core import signing
from django.urls import reverse
from .models import SiteSettings


class DeliveryError(Exception):
    pass


def send_email(recipient, subject, html, key):
    if not settings.EMAIL_READY:
        raise DeliveryError('Preview mode: connect Resend and a verified sender before sending.')
    body = json.dumps({'from': settings.EMAIL_FROM, 'to': [recipient], 'subject': subject, 'html': html}).encode()
    request = Request('https://api.resend.com/emails', data=body, headers={
        'Authorization': f'Bearer {settings.RESEND_API_KEY}', 'Content-Type': 'application/json',
        'Idempotency-Key': key, 'User-Agent': 'PetalPolish/1.0',
    }, method='POST')
    try:
        with urlopen(request, timeout=20) as response:
            result = json.load(response)
            if not result.get('id'):
                raise DeliveryError('The email provider did not acknowledge this message.')
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise DeliveryError('The email provider could not confirm acceptance. Please try again later.') from exc


def confirmation_path(subscriber):
    token = signing.dumps(str(subscriber.token), salt='email-confirmation')
    return reverse('confirm', args=[token])


def confirmation_content(subscriber):
    brand = escape(SiteSettings.load().brand_name)
    url = escape(settings.SITE_URL + confirmation_path(subscriber))
    return f'<h1>A little inspiration awaits.</h1><p>Confirm you want to receive new designs from {brand}.</p><p><a href="{url}">Confirm my subscription</a></p><p>This link expires in 48 hours. If you did not request this, ignore this email. No subscription is active until you confirm.</p>'


def notification_content(notification):
    design, subscriber = notification.design, notification.subscriber
    url = escape(settings.SITE_URL + design.get_absolute_url())
    image = escape(settings.SITE_URL + design.cover_url)
    unsubscribe = escape(settings.SITE_URL + reverse('unsubscribe', args=[subscriber.token]))
    return f'<h1>{escape(design.title)}</h1><img src="{image}" width="520" alt="{escape(design.cover_alt)}"><p>{escape(design.description[:250])}</p><p><a href="{url}">See the design</a></p><p>You asked for new nail art emails. <a href="{unsubscribe}">Unsubscribe</a> at any time.</p>'
