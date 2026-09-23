import json

from django.core.files.uploadedfile import SimpleUploadedFile

from catalog.models import Product, ProductImage
from tests.base import ShopTestCase, picture


class ProductImageCreationTests(ShopTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.admin)

    def payload(self, **extra):
        return {
            "name": "Photographed shoes",
            "category": self.category.pk,
            "base_price": "24000",
            "brand": "",
            "sale_price": "",
            "image": picture("shoes.png"),
            "new_variants": json.dumps([{"size_name": "42", "color": self.color.pk, "stock_quantity": 3}]),
            **extra,
        }

    def test_create_image_with_stock_and_publish_on_public_listing(self):
        response = self.client.post("/api/v1/dashboard/products/", self.payload(), format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        product = Product.objects.get(pk=response.data["id"])
        image = product.images.get()
        self.assertTrue(image.is_primary)
        self.assertEqual(image.alt_text, product.name)
        self.assertTrue(image.image.storage.exists(image.image.name))
        self.assertEqual(product.variants.get().stock_quantity, 3)
        self.client.force_authenticate(None)
        listing = self.client.get("/api/v1/products/", {"search": product.name}).data["results"]
        public_image = listing[0]["images"][0]
        self.assertTrue(public_image["is_primary"])
        self.assertIn(image.image.url, public_image["image"])
        self.assertEqual(
            self.client.get(f"/api/v1/products/{product.slug}/").data["images"][0]["id"], image.pk
        )

    def test_invalid_file_and_malformed_stock_do_not_create_product_or_file(self):
        cases = [
            {"image": SimpleUploadedFile("fake.png", b"not an image", content_type="image/png")},
            {"new_variants": "not JSON"},
            {"new_variants": json.dumps([{"size_name": "42", "color": self.color.pk, "stock_quantity": -1}])},
        ]
        for invalid in cases:
            response = self.client.post(
                "/api/v1/dashboard/products/", self.payload(**invalid), format="multipart"
            )
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Product.objects.filter(name="Photographed shoes").exists())
        self.assertEqual(ProductImage.objects.count(), 0)

    def test_image_can_be_saved_without_stock_rows(self):
        data = self.payload()
        del data["new_variants"]
        response = self.client.post("/api/v1/dashboard/products/", data, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(ProductImage.objects.get().product_id, response.data["id"])

    def test_invalid_stock_update_preserves_existing_primary_photo(self):
        current = ProductImage.objects.create(product=self.product, image=picture(), is_primary=True)
        response = self.client.patch(
            f"/api/v1/dashboard/products/{self.product.pk}/",
            {
                "image": picture("replacement.png"),
                "new_variants": json.dumps([{"size_name": "M", "color": self.color.pk, "stock_quantity": 4}]),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400, response.data)
        current.refresh_from_db()
        self.assertTrue(current.is_primary)
        self.assertEqual(self.product.images.count(), 1)
