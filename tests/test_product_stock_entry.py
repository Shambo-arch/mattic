from catalog.models import Product, Size
from tests.base import ShopTestCase


class ProductStockEntryTests(ShopTestCase):
    def payload(self, **extra):
        return {
            "name": "Stock entry shoes",
            "category": self.category.pk,
            "base_price": "24000",
            "new_variants": [
                {"size_name": str(size), "color": self.color.pk, "stock_quantity": quantity}
                for size, quantity in [(42, 3), (43, 5), (44, 0), (45, 2)]
            ],
            **extra,
        }

    def test_create_sizes_and_stock_together_and_publish_availability(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/v1/dashboard/products/", self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        product = Product.objects.get(pk=response.data["id"])
        self.assertEqual(product.variants.count(), 4)
        self.assertEqual(product.variants.values("sku").distinct().count(), 4)
        self.client.force_authenticate(None)
        public = self.client.get(f"/api/v1/products/{product.slug}/")
        self.assertEqual({size["name"] for size in public.data["available_sizes"]}, {"42", "43", "45"})
        self.client.force_authenticate(self.admin)
        variant = product.variants.get(size__name="42")
        changed = self.client.patch(f"/api/v1/dashboard/variants/{variant.pk}/", {"stock_quantity": 0})
        self.assertEqual(changed.status_code, 200, changed.data)
        public = self.client.get(f"/api/v1/products/{product.slug}/")
        self.assertNotIn("42", {size["name"] for size in public.data["available_sizes"]})

    def test_invalid_rows_never_create_partial_product(self):
        self.client.force_authenticate(self.admin)
        data = self.payload()
        data["new_variants"][1]["stock_quantity"] = -1
        response = self.client.post("/api/v1/dashboard/products/", data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Product.objects.filter(name=data["name"]).exists())

    def test_duplicate_existing_combination_rolls_back_all_changes(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/v1/dashboard/products/{self.product.pk}/",
            {
                "name": "Must roll back",
                "new_variants": [
                    {"size_name": "NEW", "color": self.color.pk, "stock_quantity": 1},
                    {"size_name": "M", "color": self.color.pk, "stock_quantity": 4},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "White Shirt")
        self.assertFalse(Size.objects.filter(name="NEW").exists())

    def test_customers_cannot_write_stock_and_duplicate_rows_are_rejected(self):
        response = self.client.post("/api/v1/dashboard/products/", self.payload(), format="json")
        self.assertEqual(response.status_code, 403)
        self.client.force_authenticate(self.admin)
        data = self.payload()
        data["new_variants"].append(data["new_variants"][0])
        response = self.client.post("/api/v1/dashboard/products/", data, format="json")
        self.assertEqual(response.status_code, 400)
