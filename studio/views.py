import hashlib
import uuid
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import user_passes_test
from django.core import signing
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from .models import Design, Photo, SiteSettings, Subscriber, Notification, RateLimit
from .emailing import DeliveryError, send_email, confirmation_content, confirmation_path, notification_content


def limited(request, kind, maximum):
    # Do not trust visitor-supplied forwarding headers. A shared proxy address
    # makes the limit conservative; configure a trusted real-IP proxy for launch.
    hour = timezone.now().strftime('%Y%m%d%H')
    address = request.META.get('REMOTE_ADDR', '')
    digest = hashlib.sha256((settings.SECRET_KEY + address).encode()).hexdigest()[:40]
    key = f'{hour}:{kind}:{digest}'
    RateLimit.objects.exclude(key__startswith=hour).delete()
    row, _ = RateLimit.objects.get_or_create(key=key)
    RateLimit.objects.filter(pk=row.pk).update(count=F('count') + 1)
    row.refresh_from_db()
    return row.count > maximum


def home(request):
    designs = Design.objects.filter(status='published').prefetch_related('photos')
    brand = SiteSettings.load()
    featured = designs.filter(pk=brand.featured_design_id).first() or designs.first()
    return render(request, 'studio/home.html', {'featured': featured, 'designs': designs[:6]})


def gallery(request):
    designs = Design.objects.filter(status='published').prefetch_related('photos')
    choices = {field: list(designs.order_by(field).values_list(field, flat=True).distinct()) for field in ('color', 'style', 'occasion')}
    for field in choices:
        if request.GET.get(field):
            designs = designs.filter(**{field: request.GET[field]})
    query = request.GET.get('q', '').strip()[:100]
    if query:
        designs = designs.filter(Q(title__icontains=query) | Q(description__icontains=query))
    return render(request, 'studio/gallery.html', {'designs': designs, 'choices': choices, 'query': query})


def about(request):
    return render(request, 'studio/about.html')


def design(request, slug):
    item = get_object_or_404(Design.objects.prefetch_related('photos', 'supplies'), slug=slug)
    if item.status != 'published' and not (request.user.is_active and request.user.is_superuser):
        raise Http404
    response = render(request, 'studio/design.html', {'design': item, 'steps': item.steps.splitlines(), 'has_affiliates': item.supplies.filter(affiliate=True).exists()})
    if item.status != 'published':
        response['Cache-Control'] = 'private, no-store'
        response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


def photo(request, filename):
    image = get_object_or_404(Photo.objects.select_related('design'), image='designs/' + filename)
    if image.design.status != 'published' and not (request.user.is_active and request.user.is_superuser):
        raise Http404
    response = FileResponse(image.image.open('rb'), content_type='image/webp')
    response['Cache-Control'] = 'private, no-store' if image.design.status != 'published' else 'public, max-age=3600'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@require_POST
def subscribe(request):
    if request.POST.get('website') or limited(request, 'subscribe', 5):
        return render(request, 'studio/message.html', {'heading': 'Please try again later', 'text': 'We could not accept this request. Please wait before trying again.'}, status=429)
    email = request.POST.get('email', '').strip().lower()
    try:
        validate_email(email)
        if len(email) > 254 or request.POST.get('consent') != 'yes':
            raise ValidationError('Consent is required.')
    except ValidationError:
        return render(request, 'studio/message.html', {'heading': 'A little detail is missing', 'text': 'Enter a valid email and check the consent box to continue.'}, status=400)
    if not settings.EMAIL_READY:
        return render(request, 'studio/message.html', {'heading': 'Email is in preview mode', 'text': 'Subscriptions are not active yet. Your address was not saved and no email was sent. The owner needs to connect the email service first.'}, status=503)
    subscriber, _ = Subscriber.objects.get_or_create(email=email)
    if subscriber.confirmed_at and subscriber.active:
        return render(request, 'studio/message.html', {'heading': 'Check your inbox', 'text': 'If this address needs confirmation, a confirmation email will arrive shortly. Only confirmed subscriptions receive updates.'})
    if subscriber.active and subscriber.confirmation_sent_at and subscriber.confirmation_sent_at > timezone.now() - timedelta(minutes=10):
        return render(request, 'studio/message.html', {'heading': 'Check your inbox', 'text': 'Please use the recent confirmation link, or try again in ten minutes.'})
    if not subscriber.active:
        subscriber.token = uuid.uuid4()
        subscriber.active = True
        subscriber.confirmed_at = None
        subscriber.consent_at = timezone.now()
        subscriber.save()
    try:
        send_email(subscriber.email, 'Confirm your nail art subscription', confirmation_content(subscriber), f'confirm-{subscriber.token}-{uuid.uuid4()}')
    except DeliveryError as exc:
        return render(request, 'studio/message.html', {'heading': 'Email could not be sent', 'text': str(exc) + ' Your subscription is not confirmed.'}, status=502)
    subscriber.confirmation_sent_at = timezone.now()
    subscriber.save(update_fields=['confirmation_sent_at'])
    return render(request, 'studio/message.html', {'heading': 'One more little step', 'text': 'A confirmation email was accepted by our email provider. Open it and confirm your address to receive new designs. Check spam if it does not arrive.'})


def confirm(request, token):
    try:
        value = signing.loads(token, salt='email-confirmation', max_age=48 * 3600)
        subscriber = get_object_or_404(Subscriber, token=value, active=True)
    except (signing.BadSignature, ValueError, ValidationError):
        return render(request, 'studio/message.html', {'heading': 'This link has expired', 'text': 'Please subscribe again to request a fresh confirmation link.'}, status=400)
    if request.method == 'POST':
        if subscriber.confirmation_sent_at is None:
            raise Http404
        subscriber.confirmed_at = subscriber.confirmed_at or timezone.now()
        subscriber.save(update_fields=['confirmed_at'])
        return render(request, 'studio/message.html', {'heading': 'You’re on the list', 'text': 'Your email is confirmed. Look out for a little nail art inspiration in your inbox.'})
    return render(request, 'studio/message.html', {'heading': 'Confirm your subscription', 'text': 'Choose confirm to receive new nail art emails. You can unsubscribe at any time.', 'action': 'Confirm my subscription'})


def unsubscribe(request, token):
    subscriber = get_object_or_404(Subscriber, token=token)
    if request.method == 'POST':
        subscriber.active = False
        subscriber.save(update_fields=['active'])
        return render(request, 'studio/message.html', {'heading': 'You’re unsubscribed', 'text': 'You will no longer receive nail art updates. You’re always welcome back.'})
    return render(request, 'studio/message.html', {'heading': 'A little less in your inbox?', 'text': 'Choose unsubscribe to stop receiving nail art emails.', 'action': 'Unsubscribe'})


@never_cache
def owner_login(request):
    if request.user.is_active and request.user.is_superuser:
        return redirect('owner')
    if request.method == 'POST' and limited(request, 'login', 10):
        return render(request, 'studio/message.html', {'heading': 'Please wait', 'text': 'Too many login attempts. Try again in an hour.'}, status=429)
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        if user.is_superuser:
            login(request, user)
            return redirect('owner')
        form.add_error(None, 'This account is not authorized to manage the studio.')
    return render(request, 'studio/login.html', {'form': form})


@require_POST
def owner_logout(request):
    logout(request)
    return redirect('home')


@never_cache
@user_passes_test(lambda u: u.is_active and u.is_superuser)
def owner(request):
    return render(request, 'studio/owner.html', {'designs': Design.objects.all(), 'confirmed': Subscriber.objects.filter(active=True, confirmed_at__isnull=False).count(), 'pending': Notification.objects.filter(sent_at__isnull=True, blocked=False).count()})


@never_cache
@user_passes_test(lambda u: u.is_active and u.is_superuser)
def email_preview(request):
    # An unsaved recipient makes this preview independent of private addresses.
    subscriber = Subscriber(email='preview@example.invalid')
    content = confirmation_content(subscriber)
    return render(request, 'studio/email_preview.html', {'email_html': content})


def privacy(request):
    return render(request, 'studio/privacy.html')
