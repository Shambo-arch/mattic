import tempfile
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from accounts.models import Address, User
from catalog.models import Brand, Category, Color, Product, ProductVariant, Size
from core.models import StoreSettings
from payments.models import StorePaymentSettings


def picture(name="proof.png"):
    stream = BytesIO()
    Image.new("RGB", (16, 16), "white").save(stream, format="PNG")
    return SimpleUploadedFile(name, stream.getvalue(), content_type="image/png")


class ShopTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user("customer@example.com", "StrongPassword!854")
        cls.other = User.objects.create_user("other@example.com", "StrongPassword!854")
        cls.admin = User.objects.create_superuser("owner@example.com", "StrongPassword!854")
        cls.category = Category.objects.create(name="Shirts")
        cls.brand = Brand.objects.create(name="Suit and Tie Fashion Shop")
        cls.size = Size.objects.create(name="M")
        cls.color = Color.objects.create(name="White", hex_code="#FFFFFF")
        cls.product = Product.objects.create(
            name="White Shirt",
            category=cls.category,
            brand=cls.brand,
            base_price=Decimal("10000"),
            sale_price=Decimal("9000"),
        )
        cls.variant = ProductVariant.objects.create(
            product=cls.product, size=cls.size, color=cls.color, sku="SHIRT-M-WHITE", stock_quantity=10
        )
        cls.address = Address.objects.create(
            user=cls.customer,
            full_name="Customer One",
            phone_number="0780000000",
            province="Kigali",
            district="Gasabo",
            sector="Remera",
        )
        cls.other_address = Address.objects.create(
            user=cls.other,
            full_name="Other User",
            phone_number="0780000001",
            province="Kigali",
            district="Gasabo",
            sector="Remera",
        )
        StoreSettings.objects.create(store_name="Test Shop", shipping_fee=1000, free_shipping_threshold=50000)
        StorePaymentSettings.objects.create(
            merchant_name="DEMO", momo_code="123456", payment_instructions="DEMO ONLY"
        )

    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        override = override_settings(
            MEDIA_ROOT=temporary.name + "/public", PRIVATE_MEDIA_ROOT=temporary.name + "/private"
        )
        override.enable()
        self.addCleanup(override.disable)
        self.client.force_authenticate(self.customer)

    def add(self, quantity=2):
        return self.client.post("/api/v1/cart/items/", {"variant": self.variant.pk, "quantity": quantity})

    def checkout(self, quantity=2, **extra):
        self.add(quantity)
        response = self.client.post("/api/v1/checkout/", {"shipping_address_id": self.address.pk, **extra})
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def submitted(self, quantity=2):
        order = self.checkout(quantity)
        response = self.client.post(
            f"/api/v1/orders/{order['id']}/payment-proof/", {"screenshot": picture()}, format="multipart"
        )
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def verified(self):
        order = self.submitted()
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/v1/dashboard/payments/{order['payment']['id']}/verify/", {})
        self.assertEqual(response.status_code, 200, response.data)
        return order
