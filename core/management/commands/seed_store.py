from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from catalog.models import Brand, Category, Color, Product, ProductVariant, Size
from core.models import StoreSettings
from payments.models import StorePaymentSettings


class Command(BaseCommand):
    help = "Create idempotent DEMO catalog and placeholder MoMo configuration. Creates no accounts."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {}
        for name in [
            "Suits",
            "Shirts",
            "Trousers",
            "Pants",
            "Shorts",
            "Ties",
            "Shoes",
            "Blazers",
            "Jackets",
            "Belts",
            "Socks",
            "Accessories",
        ]:
            categories[name], _ = Category.objects.get_or_create(slug=slugify(name), defaults={"name": name})
        for parent, names in {
            "Suits": ["Business Suits", "Wedding Suits", "Tuxedos"],
            "Shirts": ["Formal Shirts", "Casual Shirts", "Polo Shirts"],
            "Shoes": ["Formal Shoes", "Loafers", "Sneakers", "Boots"],
        }.items():
            for name in names:
                Category.objects.get_or_create(
                    slug=slugify(name), defaults={"name": name, "parent": categories[parent]}
                )
        colors = {}
        for name, hex_code in [
            ("Black", "#000000"),
            ("Navy Blue", "#000080"),
            ("White", "#FFFFFF"),
            ("Grey", "#808080"),
            ("Brown", "#964B00"),
            ("Beige", "#F5F5DC"),
        ]:
            colors[name], _ = Color.objects.get_or_create(name=name, defaults={"hex_code": hex_code})
        sizes = {}
        for index, name in enumerate(
            [
                "S",
                "M",
                "L",
                "XL",
                "XXL",
                "39",
                "40",
                "41",
                "42",
                "43",
                "44",
                "45",
                "46",
                "48",
                "50",
                "52",
                "54",
            ]
        ):
            sizes[name], _ = Size.objects.get_or_create(name=name, category=None, defaults={"order": index})
        brand, _ = Brand.objects.get_or_create(
            slug="suitandtiefashionshop-demo", defaults={"name": "Suit and Tie Fashion Shop Demo"}
        )
        for name, category, price, size_names, color_names in [
            ("Classic White Shirt", "Shirts", "25000", ["M", "L", "XL"], ["White", "Navy Blue"]),
            ("Navy Business Suit", "Suits", "120000", ["48", "50", "52"], ["Navy Blue", "Black"]),
            ("Leather Oxford Shoes", "Shoes", "65000", ["40", "41", "42", "43", "44"], ["Black", "Brown"]),
            ("Cotton Chino Trousers", "Trousers", "35000", ["M", "L", "XL"], ["Beige", "Navy Blue"]),
            ("Silk Occasion Tie", "Ties", "12000", ["M"], ["Navy Blue", "Grey"]),
        ]:
            product, _ = Product.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    "name": name,
                    "category": categories[category],
                    "brand": brand,
                    "base_price": Decimal(price),
                    "description": "DEMO DATA — replace with your own product description.",
                    "featured": True,
                },
            )
            for size in size_names:
                for color in color_names:
                    ProductVariant.objects.get_or_create(
                        sku=f"DEMO-{product.pk}-{size}-{slugify(color)}",
                        defaults={
                            "product": product,
                            "size": sizes[size],
                            "color": colors[color],
                            "stock_quantity": 20,
                        },
                    )
        if not StoreSettings.objects.filter(active=True).exists():
            StoreSettings.objects.create(
                store_name="Suit and Tie Fashion Shop",
                currency=settings.DEFAULT_CURRENCY,
                shipping_fee=2000,
                free_shipping_threshold=150000,
            )
        if not StorePaymentSettings.objects.filter(is_active=True).exists():
            StorePaymentSettings.objects.create(
                merchant_name="DEMO DATA — DO NOT PAY",
                momo_phone_number="0784888458",
                currency=settings.DEFAULT_CURRENCY,
                payment_instructions="DEMO ONLY. Replace these settings before accepting orders.\n"
                "1. Open MTN Mobile Money.\n2. Send money to the displayed Mobile Money number.\n3. Enter the exact order total.\n"
                "4. Complete payment.\n5. Take a screenshot.\n6. Upload it to your order for manual verification.",
            )
        self.stdout.write(
            self.style.SUCCESS(
                "DEMO DATA seeded. No credentials created. Review Mobile Money settings before launch."
            )
        )
