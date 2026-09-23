from decimal import Decimal

from cart.models import CartItem
from catalog.models import Category, Color, Product, ProductVariant, Size
from wishlist.models import WishlistItem

from .base import ShopTestCase, picture


class CatalogTests(ShopTestCase):
    def test_delete_unordered_product_cascades_variants(self):
        self.add()
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f"/api/v1/dashboard/products/{self.product.pk}/")
        self.assertEqual(response.status_code, 204, response.data)
        self.assertFalse(ProductVariant.objects.filter(pk=self.variant.pk).exists())
        self.assertEqual(CartItem.objects.count(), 0)

    def test_delete_ordered_product_is_protected(self):
        self.checkout()
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f"/api/v1/dashboard/products/{self.product.pk}/")
        self.assertEqual(response.status_code, 409, response.data)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_public_listing_details_and_search(self):
        self.client.force_authenticate(None)
        listing = self.client.get("/api/v1/products/?search=white")
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual(listing.data["count"], 1)
        product = listing.data["results"][0]
        self.assertEqual(product["variants"][0]["sku"], self.variant.sku)
        self.assertEqual(product["current_price"], "9000.00")
        self.assertTrue(product["in_stock"])
        for value in [self.product.pk, self.product.slug]:
            self.assertEqual(self.client.get(f"/api/v1/products/{value}/").status_code, 200)
        for route in ["categories", "brands", "colors", "sizes", "store", "payment-instructions"]:
            self.assertEqual(self.client.get(f"/api/v1/{route}/").status_code, 200)

    def test_filter_variant_price_and_category_descendants(self):
        child = Category.objects.create(name="Formal", parent=self.category)
        self.product.category = child
        self.product.save()
        self.variant.price = Decimal("12000")
        self.variant.save()
        for query, count in [
            (f"category={self.category.pk}", 1),
            (f"brand={self.brand.pk}", 1),
            (f"size={self.size.pk}&color={self.color.pk}", 1),
            ("min_price=10000&max_price=13000", 1),
            ("max_price=10000", 0),
            ("in_stock=true", 1),
            ("in_stock=false", 0),
            ("featured=true", 0),
            ("search=unknown", 0),
            ("ordering=price", 1),
            ("ordering=-created_at", 1),
        ]:
            with self.subTest(query=query):
                response = self.client.get("/api/v1/products/?" + query)
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data["count"], count)

    def test_size_and_color_must_match_same_variant(self):
        size = Size.objects.create(name="L")
        color = Color.objects.create(name="Black", hex_code="#000000")
        ProductVariant.objects.create(
            product=self.product, size=size, color=color, sku="SECOND", stock_quantity=2
        )
        response = self.client.get(f"/api/v1/products/?size={self.size.pk}&color={color.pk}")
        self.assertEqual(response.data["count"], 0)

    def test_inactive_product_hidden(self):
        self.product.is_active = False
        self.product.save()
        self.assertEqual(self.client.get("/api/v1/products/").data["count"], 0)
        self.assertEqual(self.client.get(f"/api/v1/products/{self.product.pk}/").status_code, 404)
        self.assertEqual(self.add().status_code, 400)

    def test_dashboard_product_image_variant_stock_and_price(self):
        self.client.force_authenticate(self.admin)
        product = self.client.post(
            "/api/v1/dashboard/products/",
            {"name": "New Shirt", "category": self.category.pk, "base_price": "15000"},
        )
        self.assertEqual(product.status_code, 201, product.data)
        product_id = product.data["id"]
        image = self.client.post(
            "/api/v1/dashboard/images/",
            {"product": product_id, "image": picture(), "is_primary": True},
            format="multipart",
        )
        self.assertEqual(image.status_code, 201, image.data)
        second = self.client.post(
            "/api/v1/dashboard/images/",
            {"product": product_id, "image": picture(), "is_primary": True},
            format="multipart",
        )
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(Product.objects.get(pk=product_id).images.filter(is_primary=True).count(), 1)
        variant = self.client.post(
            "/api/v1/dashboard/variants/",
            {
                "product": product_id,
                "size": self.size.pk,
                "color": self.color.pk,
                "sku": "NEW-SHIRT",
                "stock_quantity": 4,
            },
        )
        self.assertEqual(variant.status_code, 201, variant.data)
        self.assertEqual(
            self.client.patch(
                f"/api/v1/dashboard/inventory/{variant.data['id']}/", {"stock_quantity": 8}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/dashboard/products/{product_id}/", {"sale_price": "11000"}
            ).status_code,
            200,
        )
        public = self.client.get(f"/api/v1/products/{product_id}/")
        self.assertEqual(public.data["current_price"], "11000.00")
        self.assertEqual(public.data["variants"][0]["stock_quantity"], 8)
        self.assertEqual(len(public.data["images"]), 2)

    def test_admin_validation_and_category_cycles(self):
        self.client.force_authenticate(self.admin)
        for data in [{"sale_price": "20000"}, {"base_price": "-1"}]:
            self.assertEqual(
                self.client.patch(f"/api/v1/dashboard/products/{self.product.pk}/", data).status_code, 400
            )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/dashboard/inventory/{self.variant.pk}/", {"stock_quantity": -1}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post("/api/v1/dashboard/colors/", {"name": "Bad", "hex_code": "red"}).status_code, 400
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/dashboard/categories/{self.category.pk}/", {"parent": self.category.pk}
            ).status_code,
            400,
        )
        duplicate = self.client.post(
            "/api/v1/dashboard/variants/",
            {"product": self.product.pk, "size": self.size.pk, "color": self.color.pk, "sku": "DUPLICATE"},
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.data)


class CartWishlistTests(ShopTestCase):
    def test_cart_duplicate_update_remove_and_clear(self):
        first = self.add(2)
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(self.add(3).data["quantity"], 5)
        self.assertEqual(CartItem.objects.count(), 1)
        item_id = first.data["id"]
        update = self.client.patch(f"/api/v1/cart/items/{item_id}/", {"quantity": 4, "unit_price": "1"})
        self.assertEqual(update.status_code, 200, update.data)
        self.assertEqual(update.data["subtotal"], "36000.00")
        cart = self.client.get("/api/v1/cart/").data
        self.assertEqual(cart["total_quantity"], 4)
        self.assertEqual(cart["subtotal"], Decimal("36000"))
        self.assertEqual(self.client.delete(f"/api/v1/cart/items/{item_id}/").status_code, 204)
        self.add()
        self.assertEqual(self.client.delete("/api/v1/cart/clear/").status_code, 204)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_stock_and_quantity_validation(self):
        for quantity in [0, -1, 11]:
            self.assertEqual(self.add(quantity).status_code, 400)
        item = self.add(10).data
        self.assertEqual(self.add(1).status_code, 400)
        self.assertEqual(
            self.client.patch(f"/api/v1/cart/items/{item['id']}/", {"quantity": 11}).status_code, 400
        )
        self.assertEqual(CartItem.objects.get().quantity, 10)

    def test_cross_user_cart_and_wishlist(self):
        item = self.add().data
        wish = self.client.post("/api/v1/wishlist/items/", {"product": self.product.pk}).data
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/v1/cart/").data["total_quantity"], 0)
        self.assertEqual(
            self.client.patch(f"/api/v1/cart/items/{item['id']}/", {"quantity": 1}).status_code, 404
        )
        self.assertEqual(self.client.delete(f"/api/v1/cart/items/{item['id']}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/v1/wishlist/items/{wish['id']}/").status_code, 404)

    def test_wishlist_idempotence_and_removal(self):
        first = self.client.post("/api/v1/wishlist/items/", {"product": self.product.pk})
        second = self.client.post("/api/v1/wishlist/items/", {"product": self.product.pk})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(WishlistItem.objects.count(), 1)
        self.assertEqual(len(self.client.get("/api/v1/wishlist/").data["items"]), 1)
        self.assertEqual(self.client.delete(f"/api/v1/wishlist/items/{first.data['id']}/").status_code, 204)
        self.assertEqual(WishlistItem.objects.count(), 0)
