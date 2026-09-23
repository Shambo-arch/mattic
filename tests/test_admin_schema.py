from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from accounts.models import User
from catalog.models import Category, Product, ProductVariant

from .base import ShopTestCase


class AdministrationTests(ShopTestCase):
    @override_settings(DEBUG=False)
    def test_unexpected_api_error_is_json_and_http_500(self):
        self.client.raise_request_exception = False
        with patch(
            "cart.views.Cart.objects.get_or_create", side_effect=RuntimeError("private database detail")
        ):
            response = self.client.get("/api/v1/cart/")
        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.json()["success"])
        self.assertNotIn("private database detail", str(response.json()))

    @override_settings(DEBUG=False)
    def test_unknown_api_route_returns_json(self):
        response = self.client.get("/api/v1/missing-resource/")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()["success"])

    def test_internal_admin_login_and_model_pages(self):
        self.client.force_authenticate(None)
        self.client.force_login(self.admin)
        for model in [
            "accounts_user",
            "accounts_address",
            "catalog_product",
            "catalog_productvariant",
            "orders_order",
            "payments_payment",
            "reviews_review",
            "promotions_coupon",
            "core_storesettings",
        ]:
            response = self.client.get(reverse(f"admin:{model}_changelist"))
            self.assertEqual(response.status_code, 200, model)
        self.assertEqual(self.client.get(reverse("admin:accounts_user_add")).status_code, 200)

    def test_internal_admin_private_payment_screenshot(self):
        order = self.submitted()
        self.client.force_authenticate(None)
        url = reverse("admin:payments_payment_proof", args=[order["payment"]["id"]])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_seed_is_idempotent_and_creates_no_credentials(self):
        out = StringIO()
        users = User.objects.count()
        call_command("seed_store", stdout=out)
        counts = (Category.objects.count(), Product.objects.count(), ProductVariant.objects.count())
        call_command("seed_store", stdout=out)
        self.assertEqual(
            counts, (Category.objects.count(), Product.objects.count(), ProductVariant.objects.count())
        )
        self.assertEqual(User.objects.count(), users)

    def test_docs_and_schema_are_available(self):
        self.client.force_authenticate(None)
        for url in ["/api/docs/", "/api/redoc/", "/api/schema/"]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
