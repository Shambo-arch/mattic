from django.conf import settings
from django.db import models

from core.models import Timestamped


class Wishlist(Timestamped):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist")


class WishlistItem(Timestamped):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)

    class Meta(Timestamped.Meta):
        constraints = [
            models.UniqueConstraint(fields=["wishlist", "product"], name="unique_wishlist_product")
        ]
