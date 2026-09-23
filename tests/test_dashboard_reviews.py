from datetime import timedelta

from django.utils import timezone

from orders.models import Order
from promotions.models import Coupon
from reviews.models import Review

from .base import ShopTestCase


class FulfillmentReviewTests(ShopTestCase):
    def test_fulfillment_review_and_moderation_end_to_end(self):
        order = self.verified()
        url = f"/api/v1/dashboard/orders/{order['id']}/transition/"
        for target in ["PROCESSING", "SHIPPED", "DELIVERED"]:
            response = self.client.post(url, {"status": target})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["status"], target)
        self.assertEqual(self.client.post(url, {"status": "PROCESSING"}).status_code, 409)
        saved = Order.objects.get()
        self.assertIsNotNone(saved.shipped_at)
        self.assertIsNotNone(saved.delivered_at)
        self.client.force_authenticate(self.customer)
        data = {
            "product": self.product.pk,
            "rating": 5,
            "title": "Excellent",
            "comment": "Fits well",
            "is_approved": True,
        }
        review = self.client.post("/api/v1/reviews/", data)
        self.assertEqual(review.status_code, 201, review.data)
        self.assertFalse(review.data["is_approved"])
        self.assertEqual(self.client.post("/api/v1/reviews/", data).status_code, 400)
        self.assertEqual(self.client.get("/api/v1/reviews/").data["count"], 0)
        self.assertEqual(self.client.get(f"/api/v1/products/{self.product.pk}/").data["review_count"], 0)
        self.client.force_authenticate(self.admin)
        approve = self.client.patch(f"/api/v1/dashboard/reviews/{review.data['id']}/", {"is_approved": True})
        self.assertEqual(approve.status_code, 200, approve.data)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/v1/reviews/").data["count"], 1)
        product = self.client.get(f"/api/v1/products/{self.product.pk}/").data
        self.assertEqual(product["review_count"], 1)
        self.assertEqual(product["average_rating"], 5)

    def test_non_purchaser_and_invalid_rating_rejected(self):
        for rating in [5, 0, 6]:
            response = self.client.post(
                "/api/v1/reviews/",
                {"product": self.product.pk, "rating": rating, "title": "Test", "comment": "Test"},
            )
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Review.objects.count(), 0)

    def test_unpaid_order_cannot_skip_verification(self):
        order = self.checkout()
        self.client.force_authenticate(self.admin)
        for target in ["CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED"]:
            self.assertEqual(
                self.client.post(
                    f"/api/v1/dashboard/orders/{order['id']}/transition/", {"status": target}
                ).status_code,
                409,
            )

    def test_paid_cancellation_requires_refund_workflow(self):
        order = self.verified()
        self.assertEqual(
            self.client.post(
                f"/api/v1/dashboard/orders/{order['id']}/transition/", {"status": "CANCELLED"}
            ).status_code,
            409,
        )

    def test_cancellation_releases_coupon_once(self):
        coupon = Coupon.objects.create(
            code="DEMO",
            discount_type="FIXED",
            value=100,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
            usage_limit=1,
        )
        order = self.checkout(coupon_code=coupon.code)
        self.client.force_authenticate(self.admin)
        for _ in range(2):
            self.assertEqual(
                self.client.post(
                    f"/api/v1/dashboard/orders/{order['id']}/transition/", {"status": "CANCELLED"}
                ).status_code,
                200,
            )
        coupon.refresh_from_db()
        self.assertEqual(coupon.times_used, 0)


class DashboardTests(ShopTestCase):
    def test_summary_reports_and_customer_statistics_only_paid_revenue(self):
        self.verified()
        self.client.force_authenticate(self.customer)
        self.checkout()
        self.client.force_authenticate(self.admin)
        summary = self.client.get("/api/v1/dashboard/summary/")
        self.assertEqual(summary.status_code, 200, summary.data)
        self.assertEqual(summary.data["total_sales"], "19000.00")
        self.assertEqual(summary.data["orders_today"], 2)
        report = self.client.get("/api/v1/dashboard/reports/sales/")
        self.assertEqual(report.status_code, 200, report.data)
        self.assertEqual(report.data["total_revenue"], "19000.00")
        self.assertEqual(report.data["paid_orders"], 1)
        self.assertEqual(report.data["best_selling_products"][0]["quantity"], 2)
        customer = self.client.get(f"/api/v1/dashboard/customers/{self.customer.pk}/")
        self.assertEqual(customer.status_code, 200, customer.data)
        self.assertEqual(customer.data["number_of_orders"], 2)
        self.assertEqual(customer.data["total_spent"], "19000.00")
        self.assertNotIn("password", customer.data)
        self.assertEqual(
            self.client.get("/api/v1/dashboard/reports/sales/?date_from=2099-01-01").data["paid_orders"], 0
        )
        self.assertEqual(
            self.client.get(
                "/api/v1/dashboard/reports/sales/?date_from=2026-02-01&date_to=2026-01-01"
            ).status_code,
            400,
        )

    def test_dashboard_lists_and_filters(self):
        self.submitted()
        self.client.force_authenticate(self.admin)
        for route in [
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
        ]:
            with self.subTest(route=route):
                response = self.client.get(f"/api/v1/dashboard/{route}/")
                self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.get("/api/v1/dashboard/payments/?status=SUBMITTED").data["count"], 1)
        self.assertEqual(self.client.get("/api/v1/dashboard/payments/?status=VERIFIED").data["count"], 0)
        self.assertEqual(
            self.client.get(f"/api/v1/dashboard/orders/?customer={self.other.pk}").data["count"], 0
        )
        self.assertEqual(self.client.get("/api/v1/dashboard/inventory/?low_stock=true").data["count"], 0)
        self.assertEqual(self.client.get("/api/v1/dashboard/inventory/?out_of_stock=true").data["count"], 0)

    def test_ordered_variant_identity_is_immutable(self):
        self.checkout()
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.patch(
                f"/api/v1/dashboard/variants/{self.variant.pk}/", {"sku": "NEW-SKU"}
            ).status_code,
            400,
        )

    def test_unknown_dashboard_update_is_404(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.patch("/api/v1/dashboard/products/999999/", {"name": "Missing"}).status_code, 404
        )
