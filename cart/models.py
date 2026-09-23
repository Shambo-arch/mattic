from django.conf import settings
from django.db import models

from core.models import Timestamped


class Cart(Timestamped):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart", null=True, blank=True
    )
    guest_key = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)


class CartItem(Timestamped):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    class Meta(Timestamped.Meta):
        constraints = [
            models.UniqueConstraint(fields=["cart", "variant"], name="unique_cart_variant"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="cart_quantity_positive"),
        ]

    @property
    def unit_price(self):
        return self.variant.effective_price

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
