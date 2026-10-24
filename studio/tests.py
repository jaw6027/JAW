from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PIL import Image
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings, Client
from django.urls import reverse
from django.utils import timezone
from .emailing import confirmation_path, DeliveryError
from .models import Design, Photo, Supply, SiteSettings, Subscriber, Notification


class StudioTests(TestCase):
    def setUp(self):
        self.storage = TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.storage.name, DATA_DIR=__import__('pathlib').Path(self.storage.name))
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.storage.cleanup)
        self.owner = get_user_model().objects.create_superuser('artist', password='Only-for-testing-984!')
        self.design = Design.objects.create(title='Garden blush', slug='garden-blush', description='A floral design', color='Pink', style='Floral', occasion='Wedding')

    def publish(self):
        self.design.status = 'published'
        self.design.save()

    def upload(self):
        data = BytesIO()
        Image.new('RGB', (2400, 2000), '#dbb0bb').save(data, 'JPEG')
        return SimpleUploadedFile('phone.jpg', data.getvalue(), content_type='image/jpeg')

    def test_home_gallery_filters_and_private_draft(self):
        self.assertEqual(self.client.get(self.design.get_absolute_url()).status_code, 404)
        self.publish()
        self.assertContains(self.client.get('/'), 'Garden blush')
        self.assertContains(self.client.get('/gallery/?color=Pink'), 'Garden blush')
        self.assertNotContains(self.client.get('/gallery/?color=Gold'), 'Garden blush')
        self.assertContains(self.client.get('/gallery/?q=floral'), 'Garden blush')

    def test_owner_login_authorization_and_preview(self):
        self.assertEqual(self.client.get('/owner/').status_code, 302)
        user = get_user_model().objects.create_user('visitor', password='Only-for-testing-984!', is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.get('/owner/manage/studio/design/add/').status_code, 302)
        self.assertEqual(self.client.get(self.design.get_absolute_url()).status_code, 404)
        self.client.logout()
        response = self.client.post('/owner/login/', {'username': 'artist', 'password': 'Only-for-testing-984!'})
        self.assertRedirects(response, '/owner/')
        self.assertContains(self.client.get('/owner/'), 'The <em>studio.')
        self.assertContains(self.client.get(self.design.get_absolute_url()), 'PRIVATE DRAFT')
        self.assertIn('no-store', self.client.get(self.design.get_absolute_url())['Cache-Control'])

    def test_upload_optimization_cover_order_and_draft_photo_privacy(self):
        first = Photo.objects.create(design=self.design, image=self.upload(), alt_text='Pink floral nails', position=2, is_cover=True)
        second = Photo.objects.create(design=self.design, image=self.upload(), alt_text='Detail of a petal', position=1, is_cover=True)
        self.assertTrue(second.image.name.endswith('.webp'))
        with Image.open(second.image.path) as im:
            self.assertLessEqual(max(im.size), 1800)
            self.assertNotIn('exif', im.info)
        first.refresh_from_db()
        self.assertFalse(first.is_cover)
        self.assertEqual(self.design.cover.pk, second.pk)
        self.assertEqual(self.design.photos.first().pk, second.pk)
        self.assertEqual(self.client.get(second.image.url).status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.get(second.image.url)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.client.logout()
        self.publish()
        response = self.client.get(second.image.url)
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_real_supply_links_and_affiliate_disclosure(self):
        self.publish()
        Supply.objects.create(design=self.design, product_name='Owner-provided polish', brand='Test brand', shade='Rose', purchase_url='https://example.com/actual-product', affiliate=True)
        response = self.client.get(self.design.get_absolute_url())
        self.assertContains(response, 'https://example.com/actual-product')
        self.assertContains(response, 'Affiliate disclosure')
        self.assertContains(response, 'sponsored')
        bad = Supply(design=self.design, product_name='Bad', brand='Bad', purchase_url='javascript:alert(1)')
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            bad.full_clean()

    @override_settings(EMAIL_READY=False)
    def test_preview_never_saves_address_or_claims_delivery(self):
        response = self.client.post('/subscribe/', {'email': 'private@example.com', 'consent': 'yes'})
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, 'Your address was not saved', status_code=503)
        self.assertEqual(Subscriber.objects.count(), 0)

    @override_settings(EMAIL_READY=True)
    @patch('studio.views.send_email')
    def test_confirmation_consent_unsubscribe_and_notification_idempotency(self, sender):
        self.assertEqual(self.client.post('/subscribe/', {'email': 'reader@example.com'}).status_code, 400)
        response = self.client.post('/subscribe/', {'email': 'READER@example.com', 'consent': 'yes'})
        self.assertEqual(response.status_code, 200)
        sender.assert_called_once()
        sub = Subscriber.objects.get(email='reader@example.com')
        self.assertIsNone(sub.confirmed_at)
        path = confirmation_path(sub)
        self.client.get(path)  # Email scanners must not confirm a subscription.
        sub.refresh_from_db()
        self.assertIsNone(sub.confirmed_at)
        self.client.post(path)
        sub.refresh_from_db()
        self.assertIsNotNone(sub.confirmed_at)
        self.design.notify_subscribers = True
        self.publish()
        self.assertEqual(Notification.objects.count(), 1)
        self.design.description = 'Edited'
        self.design.save()
        self.design.status = 'draft'
        self.design.save()
        self.publish()
        self.assertEqual(Notification.objects.count(), 1)
        unsubscribe = reverse('unsubscribe', args=[sub.token])
        self.client.get(unsubscribe)
        sub.refresh_from_db()
        self.assertTrue(sub.active)
        self.client.post(unsubscribe)
        sub.refresh_from_db()
        self.assertFalse(sub.active)
        self.assertNotContains(self.client.get('/'), sub.email)

    @override_settings(EMAIL_READY=True)
    @patch('studio.views.send_email', side_effect=DeliveryError('Provider unavailable'))
    def test_email_failure_is_honest(self, sender):
        response = self.client.post('/subscribe/', {'email': 'reader@example.com', 'consent': 'yes'})
        self.assertEqual(response.status_code, 502)
        self.assertContains(response, 'Email could not be sent', status_code=502)
        self.assertIsNone(Subscriber.objects.get().confirmed_at)

    @override_settings(EMAIL_READY=True)
    @patch('studio.views.send_email')
    def test_unsubscribed_reader_can_request_fresh_confirmation_immediately(self, sender):
        sub = Subscriber.objects.create(email='returning@example.com', active=False, confirmed_at=timezone.now(), confirmation_sent_at=timezone.now())
        old_token = sub.token
        response = self.client.post('/subscribe/', {'email': sub.email, 'consent': 'yes'})
        self.assertEqual(response.status_code, 200)
        sender.assert_called_once()
        sub.refresh_from_db()
        self.assertNotEqual(sub.token, old_token)
        self.assertIsNone(sub.confirmed_at)
        self.assertEqual(self.client.post(reverse('unsubscribe', args=[old_token])).status_code, 404)

    def test_csrf_and_spam_protection(self):
        protected = Client(enforce_csrf_checks=True)
        self.assertEqual(protected.post('/subscribe/', {'email': 'reader@example.com', 'consent': 'yes'}).status_code, 403)
        self.assertEqual(self.client.post('/subscribe/', {'website': 'spam'}).status_code, 429)
        for _ in range(10):
            self.client.post('/owner/login/', {'username': 'bad', 'password': 'bad'})
        self.assertEqual(self.client.post('/owner/login/', {}).status_code, 429)

    @override_settings(EMAIL_READY=True)
    @patch('studio.emailing.urlopen')
    def test_actual_resend_request_contract(self, urlopen):
        import json
        from studio.emailing import send_email
        from unittest.mock import MagicMock
        result = MagicMock()
        result.read.return_value = b'{"id": "provider-accepted-id"}'
        urlopen.return_value.__enter__.return_value = result
        with override_settings(RESEND_API_KEY='unit-test-placeholder', EMAIL_FROM='studio@example.com'):
            send_email('reader@example.com', 'New design', '<p>Hello</p>', 'unique-delivery-key')
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.resend.com/emails')
        self.assertEqual(request.get_header('Idempotency-key'), 'unique-delivery-key')
        self.assertEqual(json.loads(request.data)['to'], ['reader@example.com'])

    @override_settings(EMAIL_READY=True)
    @patch('studio.management.commands.send_notifications.send_email')
    def test_worker_delivers_once_and_blocks_ambiguous_old_retries(self, sender):
        sub = Subscriber.objects.create(email='reader@example.com', confirmed_at=timezone.now())
        self.design.notify_subscribers = True
        self.publish()
        call_command('send_notifications', stdout=__import__('io').StringIO())
        call_command('send_notifications', stdout=__import__('io').StringIO())
        sender.assert_called_once()
        note = Notification.objects.get()
        self.assertIsNotNone(note.sent_at)
        other = Design.objects.create(title='Second', slug='second', description='New', notify_subscribers=True, status='published')
        Notification.objects.filter(design=other).update(attempted_at=timezone.now() - timedelta(hours=25))
        call_command('send_notifications', stdout=__import__('io').StringIO())
        self.assertTrue(Notification.objects.get(design=other).blocked)
        sender.assert_called_once()

    def test_samples_are_repeatable_and_never_queue_notifications(self):
        call_command('seed_samples', stdout=__import__('io').StringIO())
        call_command('seed_samples', stdout=__import__('io').StringIO())
        self.assertEqual(Design.objects.filter(is_sample=True).count(), 6)
        self.assertEqual(Notification.objects.count(), 0)
        self.assertContains(self.client.get('/'), 'illustrated placeholders')

    def test_owner_can_create_edit_and_delete_in_admin(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get('/owner/manage/studio/design/add/').status_code, 200)
        self.assertEqual(self.client.get(f'/owner/manage/studio/design/{self.design.pk}/change/').status_code, 200)
        self.assertEqual(self.client.get(f'/owner/manage/studio/design/{self.design.pk}/delete/').status_code, 200)
        self.client.post(f'/owner/manage/studio/design/{self.design.pk}/delete/', {'post': 'yes'})
        self.assertFalse(Design.objects.filter(pk=self.design.pk).exists())
