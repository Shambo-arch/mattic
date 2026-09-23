from decimal import Decimal
from uuid import uuid4

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

from .uploads import image_path, validate_image


def money_field(**kwargs):
    return models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], **kwargs
    )


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at", "-pk"]


class Named(Timestamped):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(Timestamped.Meta):
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"{slugify(self.name)[:150] or 'item'}-{uuid4().hex[:12]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class StoreSettings(Timestamped):
    store_name = models.CharField(max_length=160)
    logo = models.ImageField(upload_to=image_path, validators=[validate_image], blank=True)
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=30, blank=True)
    currency = models.CharField(max_length=3, default="RWF")
    shipping_fee = money_field(default=0)
    free_shipping_threshold = money_field(null=True, blank=True)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    active = models.BooleanField(default=True)

    class Meta(Timestamped.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["active"], condition=models.Q(active=True), name="one_active_store"
            ),
            models.CheckConstraint(condition=models.Q(shipping_fee__gte=0), name="shipping_nonnegative"),
        ]
