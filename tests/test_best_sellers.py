from catalog.models import ProductVariant, Size
from payments.models import Payment

from .base import ShopTestCase


class BestSellerTests(ShopTestCase):
    def test_only_verified_paid_orders_contribute_without_variant_join_multiplication(self):
        ProductVariant.objects.create(
            product=self.product,
            size=Size.objects.create(name="L"),
            color=self.color,
            sku="SHIRT-L-WHITE",
            stock_quantity=8,
        )
        self.submitted(quantity=3)
        response = self.client.get("/api/v1/products/?best_sellers=true&ordering=-sold_quantity")
        self.assertEqual(response.data["count"], 0)
        order = self.verified()
        response = self.client.get("/api/v1/products/?best_sellers=true&ordering=-sold_quantity")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["sold_quantity"], 2)
        Payment.objects.filter(pk=order["payment"]["id"]).update(status="REJECTED")
        response = self.client.get("/api/v1/products/?best_sellers=true")
        self.assertEqual(response.data["count"], 0)
