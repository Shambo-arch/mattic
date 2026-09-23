from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import RequestFactory, override_settings
from django.urls import reverse

from accounts.models import User

from .base import ShopTestCase


class ExclusiveOwnerTests(ShopTestCase):
    def test_configured_owner_can_access_dashboard_and_profile_capability(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/v1/dashboard/summary/").status_code, 200)
        self.assertTrue(self.client.get("/api/v1/auth/me/").data["can_access_dashboard"])

    def test_other_admin_cannot_be_created_or_promoted(self):
        with self.assertRaises(ValidationError):
            User.objects.create_superuser("second-owner@example.com", "TestPassword!492")
        self.other.role = User.Role.ADMIN
        with self.assertRaises(ValidationError):
            self.other.save()
        self.other.refresh_from_db()
        self.assertEqual(self.other.role, User.Role.CUSTOMER)

    def test_stale_admin_flags_do_not_grant_any_dashboard_access(self):
        self.client.force_login(self.other)
        # Simulate a legacy record or a direct database update bypassing model validation.
        User.objects.filter(pk=self.other.pk).update(role="ADMIN", is_staff=True, is_superuser=True)
        self.other.refresh_from_db()
        self.client.force_authenticate(self.other)
        for path in (
            "summary",
            "products",
            "categories",
            "brands",
            "colors",
            "sizes",
            "images",
            "variants",
            "inventory",
            "coupons",
            "orders",
            "payments",
            "customers",
            "reviews",
            "settings",
            "payment-settings",
            "reports/sales",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(f"/api/v1/dashboard/{path}/").status_code, 403)
        self.assertFalse(self.client.get("/api/v1/auth/me/").data["can_access_dashboard"])
        self.assertEqual(self.client.post("/api/v1/dashboard/brands/", {"name": "Denied"}).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)

    def test_stale_admin_cannot_read_other_customers_payment_proofs(self):
        order = self.submitted()
        User.objects.filter(pk=self.other.pk).update(role="ADMIN", is_staff=True, is_superuser=True)
        self.other.refresh_from_db()
        self.client.force_authenticate(self.other)
        url = f"/api/v1/payments/{order['payment']['id']}/screenshot/"
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()

    @override_settings(DASHBOARD_ADMIN_EMAIL="")
    def test_missing_owner_setting_denies_access(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/v1/dashboard/summary/").status_code, 403)
        request = RequestFactory().get("/django-admin/")
        request.user = self.admin
        self.assertFalse(admin.site.has_permission(request))

    def test_inactive_owner_is_denied(self):
        self.admin.is_active = False
        self.admin.save()
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/v1/dashboard/summary/").status_code, 403)

    def test_customer_cannot_patch_access_capability(self):
        response = self.client.patch("/api/v1/auth/me/", {"can_access_dashboard": True, "role": "ADMIN"})
        self.assertFalse(response.data["can_access_dashboard"])
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, User.Role.CUSTOMER)

    @override_settings(DASHBOARD_ADMIN_EMAIL=" OWNER@EXAMPLE.COM ")
    def test_email_matching_is_case_insensitive(self):
        self.assertTrue(self.admin.can_access_dashboard)
        self.admin.save()
