from django.core.management.base import BaseCommand
from studio.models import Design, SiteSettings, Supply


class Command(BaseCommand):
    help = 'Add clearly labeled illustrative samples without overwriting existing content.'

    def handle(self, *args, **options):
        settings = SiteSettings.load()
        samples = [
            ('petal-soft', 'Petal soft', 'Blush', 'Floral', 'Everyday', 'Soft blush tones and tiny ivory petals. A little reminder that the smallest details can make the loveliest statement.'),
            ('a-french-kind-of-day', 'A French kind of day', 'Cream', 'French', 'Wedding', 'An understated cream palette with a delicate French tip. Clean lines, warm neutrals, and an effortless finish.'),
            ('after-hours', 'After hours', 'Plum', 'Abstract', 'Evening', 'Rich plum meets a delicate sweeping line. A moody color study for evenings that deserve a little extra detail.'),
            ('a-touch-of-gold', 'A touch of gold', 'Gold', 'Minimal', 'Celebration', 'Warm caramel shades and fine golden traces. A simple way to bring a little shimmer to a special moment.'),
            ('sage-daydream', 'Sage daydream', 'Green', 'Minimal', 'Everyday', 'A quiet palette of sage and soft green, finished with a tiny golden detail. Inspired by slow mornings and garden walks.'),
            ('cherry-on-top', 'Cherry on top', 'Pink', 'Floral', 'Celebration', 'Rosy pinks and playful petals bring a little joy to this illustrative color study. Sweet, soft, and full of possibility.'),
        ]
        first = None
        for i, (slug, title, color, style, occasion, description) in enumerate(samples, 1):
            design, created = Design.objects.get_or_create(slug=slug, defaults={
                'title': title, 'description': description + '\n\nSample design: this illustration demonstrates the journal layout. It is not a photograph of the owner’s nail art.',
                'color': color, 'style': style, 'occasion': occasion, 'is_sample': True, 'sample_art': i, 'status': 'published',
                'steps': 'Prepare clean nails and apply a suitable base coat.\nApply your chosen shade in thin coats, following the product instructions.\nAdd your chosen detail with a fine brush.\nFinish with a compatible top coat. Follow all manufacturer safety and curing instructions.',
            })
            if created:
                Supply.objects.create(design=design, product_name='Color polish — example', brand='Your favorite brand', shade=color, notes='Sample supply. Add the actual product and retailer link when you publish your own design.')
                Supply.objects.create(design=design, product_name='Fine detail brush — example', brand='Your favorite brand', notes='Sample tool. No purchase URL has been invented.')
            first = first or design
        if not settings.featured_design:
            settings.featured_design = first
            settings.save()
        self.stdout.write('Sample designs available. Existing designs and brand text preserved.')
