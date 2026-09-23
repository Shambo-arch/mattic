from django.core.cache import cache

from accounts.models import User

from .base import ShopTestCase


class AuthenticationTests(ShopTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_register_login_refresh_logout_and_profile(self):
        self.client.force_authenticate(None)
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "email": "New@Example.com",
                "password": "Complex!Password937",
                "first_name": "New",
                "role": "ADMIN",
                "is_staff": True,
            },
        )
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.role, "CUSTOMER")
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password("Complex!Password937"))
        login = self.client.post(
            "/api/v1/auth/login/", {"email": "NEW@example.com", "password": "Complex!Password937"}
        )
        self.assertEqual(login.status_code, 200, login.data)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + login.data["access"])
        profile = self.client.patch("/api/v1/auth/me/", {"first_name": "Updated", "role": "ADMIN"})
        self.assertEqual(profile.data["first_name"], "Updated")
        self.assertEqual(profile.data["role"], "CUSTOMER")
        refresh = self.client.post("/api/v1/auth/token/refresh/", {"refresh": login.data["refresh"]})
        self.assertEqual(refresh.status_code, 200, refresh.data)
        self.assertEqual(
            self.client.post("/api/v1/auth/token/refresh/", {"refresh": login.data["refresh"]}).status_code,
            401,
        )
        self.assertEqual(
            self.client.post("/api/v1/auth/logout/", {"refresh": refresh.data["refresh"]}).status_code, 204
        )
        self.assertEqual(
            self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh.data["refresh"]}).status_code,
            401,
        )

    def test_duplicate_email_and_weak_password_rejected(self):
        for payload in [
            {"email": "CUSTOMER@example.com", "password": "StrongPassword!854"},
            {"email": "new@example.com", "password": "12345678"},
        ]:
            self.assertEqual(self.client.post("/api/v1/auth/register/", payload).status_code, 400)

    def test_anonymous_protected_routes(self):
        self.client.force_authenticate(None)
        for path in ["auth/me/", "cart/", "wishlist/", "orders/", "addresses/", "dashboard/summary/"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get("/api/v1/" + path).status_code, 401)

    def test_customer_blocked_from_every_dashboard_resource(self):
        for path in [
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
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get("/api/v1/dashboard/" + path + "/").status_code, 403)

    def test_cross_user_addresses_and_default_switch(self):
        foreign = f"/api/v1/addresses/{self.other_address.pk}/"
        for response in [
            self.client.get(foreign),
            self.client.patch(foreign, {"full_name": "Changed"}),
            self.client.delete(foreign),
        ]:
            self.assertEqual(response.status_code, 404)
        self.client.patch(f"/api/v1/addresses/{self.address.pk}/", {"is_default": True})
        response = self.client.post(
            "/api/v1/addresses/",
            {
                "full_name": "New",
                "phone_number": "0780000000",
                "province": "Kigali",
                "district": "Gasabo",
                "sector": "Remera",
                "is_default": True,
                "user": self.other.pk,
            },
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.customer.addresses.filter(is_default=True).count(), 1)
        self.assertEqual(self.other.addresses.count(), 1)

    def test_inactive_user_cannot_login(self):
        self.customer.is_active = False
        self.customer.save()
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.post(
                "/api/v1/auth/login/", {"email": self.customer.email, "password": "StrongPassword!854"}
            ).status_code,
            401,
        )

    def test_response_envelope(self):
        response = self.client.get("/api/v1/cart/")
        self.assertEqual(set(response.json()), {"success", "message", "data"})
        self.assertTrue(response.json()["success"])
        error = self.client.get("/api/v1/dashboard/summary/")
        self.assertFalse(error.json()["success"])
        self.assertIn("errors", error.json())
