import uuid
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse


class SiteSettings(models.Model):
    brand_name = models.CharField(max_length=80, default='Petal & Polish')
    tagline = models.CharField(max_length=180, default='A little color. A little detail. A little you.')
    biography = models.TextField(default='Welcome to my little corner of color. This is a space for nail art, thoughtful details, and finding a little inspiration in the everyday. Make yourself at home.\n\nThis is a sample biography. The owner can replace it in the dashboard.')
    instagram = models.URLField(blank=True)
    pinterest = models.URLField(blank=True)
    tiktok = models.URLField(blank=True)
    featured_design = models.ForeignKey('Design', null=True, blank=True, on_delete=models.SET_NULL)

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def save(self, *args, **kwargs):
        self.pk = 1
        return super().save(*args, **kwargs)

    def __str__(self):
        return 'Brand, biography & social links'


class Design(models.Model):
    STATUS = [('draft', 'Draft'), ('published', 'Published')]
    title = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, max_length=180, help_text='The shareable address. Keep it unchanged after sharing.')
    description = models.TextField()
    steps = models.TextField(blank=True, help_text='Optional. Put each step on its own line.')
    color = models.CharField(max_length=40, default='Blush')
    style = models.CharField(max_length=40, default='Minimal')
    occasion = models.CharField(max_length=40, default='Everyday')
    status = models.CharField(max_length=12, choices=STATUS, default='draft')
    published_at = models.DateTimeField(null=True, blank=True)
    notify_subscribers = models.BooleanField(default=False, help_text='On first publication, queue one email per confirmed subscriber. Sample designs never send.')
    notification_started = models.BooleanField(default=False, editable=False)
    is_sample = models.BooleanField(default=False, help_text='Clearly label illustrative sample content. Turn off for your own work.')
    sample_art = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('design', args=[self.slug])

    def save(self, *args, **kwargs):
        from django.db import transaction
        from django.utils import timezone
        with transaction.atomic():
            first_publish = self.status == 'published' and not self.notification_started
            if first_publish:
                self.published_at = self.published_at or timezone.now()
                self.notification_started = True
            result = super().save(*args, **kwargs)
            if first_publish and self.notify_subscribers and not self.is_sample:
                Notification.objects.bulk_create([
                    Notification(design=self, subscriber=s)
                    for s in Subscriber.objects.filter(active=True, confirmed_at__isnull=False)
                ], ignore_conflicts=True)
            return result

    @property
    def cover(self):
        return self.photos.order_by('-is_cover', 'position', 'pk').first()

    @property
    def cover_url(self):
        photo = self.cover
        return photo.image.url if photo else f'{settings.STATIC_URL}studio/sample-{self.sample_art if self.sample_art in range(1, 7) else 1}.svg'

    @property
    def cover_alt(self):
        return self.cover.alt_text if self.cover else 'Illustrative nail shapes — placeholder, not original nail art'


class Photo(models.Model):
    design = models.ForeignKey(Design, related_name='photos', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='designs/')
    alt_text = models.CharField(max_length=250, help_text='Describe this photo for visitors using screen readers.')
    position = models.PositiveIntegerField(default=0, help_text='Lower numbers appear first.')
    is_cover = models.BooleanField(default=False)

    class Meta:
        ordering = ['position', 'pk']

    def clean(self):
        if self.image and not self.image._committed:
            if self.image.size > 10 * 1024 * 1024:
                raise ValidationError({'image': 'Use a photo smaller than 10 MB.'})
            try:
                with Image.open(self.image) as im:
                    if im.width * im.height > 40_000_000:
                        raise ValidationError({'image': 'Choose a photo smaller than 40 megapixels.'})
                    im.verify()
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
                raise ValidationError({'image': 'Upload a valid JPEG, PNG or WebP photo.'}) from exc
            finally:
                self.image.seek(0)

    def save(self, *args, **kwargs):
        if self.image and not self.image._committed:
            self.clean()
            self.image.seek(0)
            with Image.open(self.image) as im:
                im = ImageOps.exif_transpose(im).convert('RGB')
                im.thumbnail((1800, 1800))
                output = BytesIO()
                im.save(output, 'WEBP', quality=84, method=4)
            self.image = ContentFile(output.getvalue(), name=f'{uuid.uuid4().hex}.webp')
        result = super().save(*args, **kwargs)
        if self.is_cover:
            Photo.objects.filter(design=self.design).exclude(pk=self.pk).update(is_cover=False)
        return result


class Supply(models.Model):
    design = models.ForeignKey(Design, related_name='supplies', on_delete=models.CASCADE)
    product_name = models.CharField(max_length=150)
    brand = models.CharField(max_length=100)
    shade = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    purchase_url = models.URLField(blank=True, help_text='Paste the real retailer product URL. Leave empty when unavailable.')
    affiliate = models.BooleanField(default=False)

    def clean(self):
        if self.purchase_url and not self.purchase_url.startswith('https://'):
            raise ValidationError({'purchase_url': 'Use a secure https:// retailer link.'})

    def __str__(self):
        return self.product_name


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    consent_at = models.DateTimeField(auto_now_add=True)
    consent_text = models.CharField(max_length=200, default='I agree to receive nail art emails. I can unsubscribe at any time.')
    confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return 'Private subscriber'


class Notification(models.Model):
    design = models.ForeignKey(Design, on_delete=models.CASCADE)
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempted_at = models.DateTimeField(null=True, blank=True)
    blocked = models.BooleanField(default=False)
    last_error = models.CharField(max_length=200, blank=True)
    subject_snapshot = models.CharField(max_length=250, blank=True)
    html_snapshot = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['design', 'subscriber'], name='one_email_per_design_subscriber')]


class RateLimit(models.Model):
    key = models.CharField(max_length=100, unique=True)
    count = models.PositiveIntegerField(default=0)
