from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from cart.models import CartItem
from catalog.models import ProductVariant, Size
from core.models import StoreSettings
from orders.models import Order
from payments.models import Payment, StorePaymentSettings
from promotions.models import Coupon

from .base import ShopTestCase, picture


class CheckoutTests(ShopTestCase):
    def coupon(self, **extra):
        defaults = {
            "code": "SAVE10",
            "discount_type": "PERCENTAGE",
            "value": 10,
            "start_date": timezone.now() - timedelta(days=1),
            "end_date": timezone.now() + timedelta(days=1),
            "usage_limit": 2,
        }
        return Coupon.objects.create(**{**defaults, **extra})

    def test_checkout_snapshots_payment_and_server_totals(self):
        order = self.checkout(total_amount="1", payment_status="PAID")
        self.assertEqual(order["subtotal"], "18000.00")
        self.assertEqual(order["total_amount"], "19000.00")
        self.assertEqual(order["payment_status"], "UNPAID")
        self.assertEqual(order["payment"]["status"], "PENDING")
        self.assertEqual(order["payment"]["instructions_snapshot"]["momo_phone_number"], "0784888458")
        self.assertTrue(order["order_number"].startswith("MEN-"))
        self.assertEqual(CartItem.objects.count(), 0)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 10)
        self.product.name = "Changed Name"
        self.product.base_price = Decimal("30000")
        self.product.save()
        self.address.district = "Changed district"
        self.address.save()
        StorePaymentSettings.objects.update(momo_phone_number="0780000001")
        detail = self.client.get(f"/api/v1/orders/{order['id']}/").data
        self.assertEqual(detail["items"][0]["product_name"], "White Shirt")
        self.assertEqual(detail["items"][0]["unit_price"], "9000.00")
        self.assertEqual(detail["shipping_address"]["district"], "Gasabo")
        self.assertEqual(detail["payment"]["instructions_snapshot"]["momo_phone_number"], "0784888458")

    def test_percentage_coupon_and_free_shipping(self):
        coupon = self.coupon()
        order = self.checkout(coupon_code="save10")
        self.assertEqual(order["discount"], "1800.00")
        self.assertEqual(order["total_amount"], "17200.00")
        coupon.refresh_from_db()
        self.assertEqual(coupon.times_used, 1)
        order = self.checkout(quantity=7)
        self.assertEqual(order["shipping_cost"], "0.00")

    def test_fixed_discount_is_capped_at_subtotal(self):
        self.coupon(discount_type="FIXED", value=99999)
        order = self.checkout(coupon_code="SAVE10")
        self.assertEqual(order["discount"], "18000.00")
        self.assertEqual(order["total_amount"], "1000.00")

    def test_coupon_expiry_minimum_limit_and_unknown(self):
        coupon = self.coupon()
        self.add()
        for changes in [
            {"is_active": False},
            {"is_active": True, "minimum_order": 100000},
            {"minimum_order": 0, "times_used": 2},
            {"times_used": 0, "end_date": timezone.now() - timedelta(hours=1)},
        ]:
            Coupon.objects.filter(pk=coupon.pk).update(**changes)
            response = self.client.post(
                "/api/v1/checkout/", {"shipping_address_id": self.address.pk, "coupon_code": "SAVE10"}
            )
            self.assertEqual(response.status_code, 400, response.data)
            self.assertEqual(Order.objects.count(), 0)
            self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(
            self.client.post(
                "/api/v1/checkout/", {"shipping_address_id": self.address.pk, "coupon_code": "UNKNOWN"}
            ).status_code,
            400,
        )

    def test_empty_cart_and_wrong_address(self):
        self.assertEqual(
            self.client.post("/api/v1/checkout/", {"shipping_address_id": self.address.pk}).status_code, 400
        )
        self.add()
        self.assertEqual(
            self.client.post("/api/v1/checkout/", {"shipping_address_id": self.other_address.pk}).status_code,
            404,
        )
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_rechecks_stock_and_configuration(self):
        self.add()
        self.variant.stock_quantity = 1
        self.variant.save()
        self.assertEqual(
            self.client.post("/api/v1/checkout/", {"shipping_address_id": self.address.pk}).status_code, 400
        )
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(CartItem.objects.count(), 1)
        StoreSettings.objects.update(currency="USD")
        self.assertEqual(
            self.client.post("/api/v1/checkout/", {"shipping_address_id": self.address.pk}).status_code, 409
        )

    def test_failure_rolls_back_order_coupon_and_cart(self):
        coupon = self.coupon()
        self.add()
        with patch("orders.services.Payment.objects.create", side_effect=RuntimeError("Storage unavailable")):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    "/api/v1/checkout/", {"shipping_address_id": self.address.pk, "coupon_code": coupon.code}
                )
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(CartItem.objects.count(), 1)
        coupon.refresh_from_db()
        self.assertEqual(coupon.times_used, 0)


class PaymentTests(ShopTestCase):
    def test_upload_and_private_download(self):
        order = self.submitted()
        self.assertEqual(order["status"], "PAYMENT_SUBMITTED")
        self.assertEqual(order["payment_status"], "PENDING_VERIFICATION")
        self.assertEqual(order["payment"]["status"], "SUBMITTED")
        url = f"/api/v1/payments/{order['payment']['id']}/screenshot/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        response.close()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(url).status_code, 401)
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_invalid_image_extension_content_and_size(self):
        order = self.checkout()
        for upload in [
            SimpleUploadedFile("virus.exe", b"not an image"),
            SimpleUploadedFile("fake.png", b"not an image"),
            picture("wrong.jpg"),
            SimpleUploadedFile(
                "large.png", picture().read() + b"x" * (5 * 1024 * 1024), content_type="image/png"
            ),
        ]:
            response = self.client.post(
                f"/api/v1/orders/{order['id']}/payment-proof/", {"screenshot": upload}, format="multipart"
            )
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Payment.objects.get().status, "PENDING")

    def test_cross_user_orders_and_proof(self):
        order = self.checkout()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/v1/orders/").data["count"], 0)
        self.assertEqual(self.client.get(f"/api/v1/orders/{order['id']}/").status_code, 404)
        self.assertEqual(
            self.client.post(
                f"/api/v1/orders/{order['id']}/payment-proof/", {"screenshot": picture()}, format="multipart"
            ).status_code,
            404,
        )

    def test_verify_once_and_prevent_double_deduction(self):
        order = self.submitted()
        url = f"/api/v1/dashboard/payments/{order['payment']['id']}/verify/"
        self.assertEqual(self.client.post(url, {}).status_code, 403)
        self.client.force_authenticate(self.admin)
        for _ in range(2):
            response = self.client.post(url, {"admin_note": "Confirmed in merchant records"})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["status"], "VERIFIED")
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 8)
        saved = Order.objects.get(pk=order["id"])
        self.assertEqual(saved.status, "CONFIRMED")
        self.assertEqual(saved.payment_status, "PAID")
        self.assertTrue(saved.stock_deducted)
        self.assertIsNotNone(saved.confirmed_at)
        self.assertEqual(saved.payment.verified_by, self.admin)

    def test_insufficient_stock_keeps_payment_unverified(self):
        order = self.submitted()
        self.variant.stock_quantity = 1
        self.variant.save()
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/v1/dashboard/payments/{order['payment']['id']}/verify/", {})
        self.assertEqual(response.status_code, 400, response.data)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 1)
        self.assertEqual(Payment.objects.get().status, "SUBMITTED")
        self.assertFalse(Order.objects.get().stock_deducted)

    def test_multi_item_stock_failure_rolls_back_all_deductions(self):
        size = Size.objects.create(name="L")
        second = ProductVariant.objects.create(
            product=self.product, size=size, color=self.color, sku="SECOND", stock_quantity=2
        )
        self.client.post("/api/v1/cart/items/", {"variant": second.pk, "quantity": 2})
        order = self.submitted()
        second.stock_quantity = 0
        second.save()
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.post(f"/api/v1/dashboard/payments/{order['payment']['id']}/verify/", {}).status_code,
            400,
        )
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 10)

    def test_rejection_and_resubmission(self):
        order = self.submitted()
        self.client.force_authenticate(self.admin)
        reject = self.client.post(
            f"/api/v1/dashboard/payments/{order['payment']['id']}/reject/", {"admin_note": "Unreadable image"}
        )
        self.assertEqual(reject.status_code, 200, reject.data)
        self.assertEqual(reject.data["status"], "REJECTED")
        self.assertEqual(Order.objects.get().payment_status, "REJECTED")
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            f"/api/v1/orders/{order['id']}/payment-proof/",
            {"screenshot": picture(), "transaction_reference": "DEMO-REF"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["payment"]["status"], "SUBMITTED")
        self.assertEqual(response.data["payment"]["transaction_reference"], "DEMO-REF")
        self.assertEqual(response.data["payment"]["admin_note"], "")

    def test_cannot_replace_submitted_or_verified_proof(self):
        order = self.submitted()
        url = f"/api/v1/orders/{order['id']}/payment-proof/"
        self.assertEqual(
            self.client.post(url, {"screenshot": picture()}, format="multipart").status_code, 409
        )
        self.client.force_authenticate(self.admin)
        self.client.post(f"/api/v1/dashboard/payments/{order['payment']['id']}/verify/", {})
        self.client.force_authenticate(self.customer)
        self.assertEqual(
            self.client.post(url, {"screenshot": picture()}, format="multipart").status_code, 409
        )

    def test_pending_payment_cannot_be_verified(self):
        order = self.checkout()
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.post(f"/api/v1/dashboard/payments/{order['payment']['id']}/verify/", {}).status_code,
            409,
        )

    def test_cancelled_order_cannot_be_paid(self):
        order = self.submitted()
        self.client.force_authenticate(self.admin)
        cancelled = self.client.post(
            f"/api/v1/dashboard/orders/{order['id']}/transition/", {"status": "CANCELLED"}
        )
        self.assertEqual(cancelled.status_code, 200, cancelled.data)
        self.assertEqual(
            self.client.post(f"/api/v1/dashboard/payments/{order['payment']['id']}/verify/", {}).status_code,
            409,
        )
