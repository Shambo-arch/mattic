import hashlib

from rest_framework.test import APIClient

from accounts.models import Address, User
from cart.models import Cart
from orders.models import Order

from .base import ShopTestCase, picture


class GuestCheckoutTests(ShopTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(None)
        self.token = "a" * 64
        self.client.credentials(HTTP_X_GUEST_TOKEN=self.token)
        self.delivery = {
            "full_name": "Guest Shopper",
            "phone_number": "0780000000",
            "country": "Rwanda",
            "province": "Kigali",
            "district": "Gasabo",
            "sector": "Remera",
        }

    def guest_checkout(self):
        self.assertEqual(self.add().status_code, 201)
        response = self.client.post("/api/v1/checkout/", {"guest_address": self.delivery}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_guest_checkout_proof_and_admin_verification_without_account(self):
        users, addresses = User.objects.count(), Address.objects.count()
        order = self.guest_checkout()
        self.assertEqual(User.objects.count(), users)
        self.assertEqual(Address.objects.count(), addresses)
        self.assertEqual(order["total_amount"], "19000.00")
        self.assertEqual(order["customer_name"], "Guest Shopper")
        self.assertEqual(order["payment"]["instructions_snapshot"]["momo_phone_number"], "0784888458")
        self.assertNotIn("momo_code", order["payment"]["instructions_snapshot"])
        self.assertNotIn("guest_key", order)
        record = Order.objects.get(pk=order["id"])
        self.assertIsNone(record.user_id)
        self.assertEqual(record.guest_key, hashlib.sha256(self.token.encode()).hexdigest())
        response = self.client.post(
            f"/api/v1/orders/{record.pk}/payment-proof/", {"screenshot": picture()}, format="multipart"
        )
        self.assertEqual(response.status_code, 200, response.data)
        proof_url = response.data["payment"]["screenshot_url"]
        download = self.client.get(proof_url)
        self.assertEqual(download.status_code, 200)
        download.close()
        stranger = APIClient()
        stranger.credentials(HTTP_X_GUEST_TOKEN="b" * 64)
        self.assertEqual(stranger.get(proof_url).status_code, 404)
        self.client.force_authenticate(self.admin)
        admin_detail = self.client.get(f"/api/v1/dashboard/orders/{record.pk}/")
        self.assertEqual(admin_detail.data["customer_email"], "Guest checkout")
        self.assertNotIn("guest_key", admin_detail.data)
        payment = order["payment"]["id"]
        self.assertEqual(
            self.client.get(f"/api/v1/dashboard/payments/{payment}/").data["customer"], "Guest: Guest Shopper"
        )
        verified = self.client.post(f"/api/v1/dashboard/payments/{payment}/verify/", {})
        self.assertEqual(verified.status_code, 200, verified.data)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 8)
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_X_GUEST_TOKEN=self.token)
        self.assertEqual(self.client.get(f"/api/v1/orders/{record.pk}/").data["payment_status"], "PAID")

    def test_guest_sessions_isolate_carts_orders_and_proof_submission(self):
        item = self.add().data
        stranger = APIClient()
        stranger.credentials(HTTP_X_GUEST_TOKEN="b" * 64)
        self.assertEqual(stranger.get("/api/v1/cart/").data["items"], [])
        self.assertEqual(
            stranger.patch(f"/api/v1/cart/items/{item['id']}/", {"quantity": 1}).status_code, 404
        )
        response = self.client.post("/api/v1/checkout/", {"guest_address": self.delivery}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        url = f"/api/v1/orders/{response.data['id']}/"
        self.assertEqual(stranger.get(url).status_code, 404)
        self.assertEqual(stranger.get("/api/v1/orders/").data["count"], 0)
        self.assertEqual(
            stranger.post(url + "payment-proof/", {"screenshot": picture()}, format="multipart").status_code,
            404,
        )
        stranger.force_authenticate(self.other)
        stranger.credentials(HTTP_X_GUEST_TOKEN=self.token)
        self.assertEqual(stranger.get(url).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/orders/").data["count"], 1)

    def test_guest_requires_valid_delivery_and_cannot_access_accounts_or_admin(self):
        self.add()
        for data in [
            {},
            {"shipping_address_id": self.address.pk},
            {"guest_address": {"full_name": "Incomplete"}},
        ]:
            response = self.client.post("/api/v1/checkout/", data, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.client.get("/api/v1/dashboard/orders/").status_code, 401)
        self.client.credentials(HTTP_X_GUEST_TOKEN="invalid")
        self.assertEqual(self.client.get("/api/v1/cart/").status_code, 401)
        self.client.credentials()
        self.assertEqual(self.client.get("/api/v1/orders/").status_code, 401)
        self.assertEqual(Cart.objects.count(), 1)
