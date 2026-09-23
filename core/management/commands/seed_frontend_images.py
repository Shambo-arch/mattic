from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from catalog.models import Product, ProductImage


class Command(BaseCommand):
    help = (
        "Attach generated demo photos to seeded Suit and Tie Fashion Shop Demo products without replacing images."
    )

    def handle(self, *args, **options):
        assets = Path(settings.BASE_DIR) / "frontend" / "public" / "images"
        mapping = {
            "classic-white-shirt": "shirt.png",
            "navy-business-suit": "suit.png",
            "leather-oxford-shoes": "shoes.png",
            "cotton-chino-trousers": "trousers.png",
        }
        count = 0
        for slug, filename in mapping.items():
            product = Product.objects.filter(slug=slug, brand__slug="suitandtiefashionshop-demo").first()
            source = assets / filename
            if not product or not source.is_file():
                continue
            if not product.images.exists():
                with source.open("rb") as stream:
                    ProductImage.objects.create(
                        product=product,
                        image=File(stream, name=filename),
                        alt_text=f"DEMO illustration of {product.name}",
                        is_primary=True,
                    )
                count += 1
            if not product.category.image:
                with source.open("rb") as stream:
                    product.category.image.save(filename, File(stream), save=True)
        self.stdout.write(
            self.style.SUCCESS(f"Attached {count} demo product photos. Existing images preserved.")
        )
