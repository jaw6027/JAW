from django.contrib import admin
from django.utils.html import format_html
from .models import Design, Photo, Supply, SiteSettings, Subscriber, Notification

admin.site.site_header = 'Your nail art studio'
admin.site.site_title = 'Owner studio'
admin.site.index_title = 'Create something lovely'
# Only the authorized owner (superuser), never an ordinary account, can edit.
admin.site.has_permission = lambda request: request.user.is_active and request.user.is_superuser


class PhotoInline(admin.StackedInline):
    model = Photo
    extra = 1
    fields = ('image', 'alt_text', 'position', 'is_cover')


class SupplyInline(admin.StackedInline):
    model = Supply
    extra = 1


@admin.register(Design)
class DesignAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'is_sample', 'published_at', 'preview_link')
    list_filter = ('status', 'is_sample', 'color', 'style', 'occasion')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('published_at', 'preview_link', 'email_status')
    inlines = [PhotoInline, SupplyInline]
    fieldsets = (
        ('Your design', {'fields': ('title', 'slug', 'description', 'steps')}),
        ('Gallery filters', {'fields': ('color', 'style', 'occasion')}),
        ('Publish when ready', {'fields': ('status', 'notify_subscribers', 'published_at', 'preview_link', 'email_status'), 'description': 'Choose Draft to save privately or unpublish. Save first, then use Preview design. Emails are queued only on first publication when the notification box is selected. Run the email worker to deliver queued messages.'}),
        ('Sample content', {'fields': ('is_sample', 'sample_art'), 'classes': ('collapse',)}),
    )

    def preview_link(self, obj):
        return format_html('<a href="{}" target="_blank">Preview design ↗</a>', obj.get_absolute_url()) if obj.pk else 'Save as a draft to preview.'

    def email_status(self, obj):
        if not obj.pk:
            return 'Not published yet.'
        return f'{obj.notification_set.filter(sent_at__isnull=False).count()} accepted by email provider; {obj.notification_set.filter(sent_at__isnull=True, blocked=False).count()} queued; {obj.notification_set.filter(blocked=True).count()} need review.'


@admin.register(SiteSettings)
class SettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'confirmed_at', 'active', 'consent_at')
    readonly_fields = ('email', 'token', 'confirmed_at', 'consent_at', 'consent_text', 'confirmation_sent_at')
    fields = readonly_fields + ('active',)

    def has_add_permission(self, request):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('design', 'sent_at', 'attempted_at', 'blocked', 'last_error')
    readonly_fields = ('design', 'subscriber', 'sent_at', 'attempted_at', 'blocked', 'last_error')

    def has_add_permission(self, request):
        return False
