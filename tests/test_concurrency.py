from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from rest_framework.exceptions import ValidationError

from accounts.models import Address, User
from cart.services import add_item
from catalog.models import Category, Color, Product, ProductVariant, Size
from core.models import StoreSettings
from orders.models import Order
from orders.services import checkout
from payments.models import Payment, StorePaymentSettings
from payments.services import verify_payment


@skipUnless(connection.vendor == "postgresql", "PostgreSQL is required to exercise row-lock concurrency.")
class VerificationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user("buyer@example.com", "password")
        self.admin = User.objects.create_superuser("owner@example.com", "password")
        category = Category.objects.create(name="Shirts")
        product = Product.objects.create(name="Shirt", category=category, base_price=100)
        self.variant = ProductVariant.objects.create(
            product=product,
            size=Size.objects.create(name="M"),
            color=Color.objects.create(name="White", hex_code="#FFFFFF"),
            sku="RACE",
            stock_quantity=5,
        )
        self.address = Address.objects.create(
            user=self.user,
            full_name="Buyer",
            phone_number="123",
            province="Kigali",
            district="Gasabo",
            sector="Remera",
        )
        StoreSettings.objects.create(store_name="Test")
        StorePaymentSettings.objects.create(
            merchant_name="DEMO", momo_code="123456", payment_instructions="DEMO"
        )

    def payment(self):
        add_item(self.user, self.variant.pk, 4)
        order = checkout(self.user, self.address.pk)
        Order.objects.filter(pk=order.pk).update(
            status="PAYMENT_SUBMITTED", payment_status="PENDING_VERIFICATION"
        )
        Payment.objects.filter(order=order).update(status="SUBMITTED", screenshot="fixture.png")
        return Payment.objects.get(order=order).pk

    def race(self, ids):
        barrier = Barrier(2)

        def worker(payment_id):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                verify_payment(payment_id, self.admin)
                return "verified"
            except ValidationError:
                return "insufficient_stock"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(worker, ids))

    def test_same_payment_concurrently_deducts_once(self):
        payment = self.payment()
        self.assertEqual(self.race([payment, payment]), ["verified", "verified"])
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 1)

    def test_competing_orders_cannot_oversell(self):
        results = self.race([self.payment(), self.payment()])
        self.assertCountEqual(results, ["verified", "insufficient_stock"])
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 1)
        self.assertEqual(Payment.objects.filter(status="VERIFIED").count(), 1)
