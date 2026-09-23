from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import Timestamped, money_field


def order_number():
    return f"MEN-{timezone.localdate():%Y%m%d}-{uuid4().hex[:16].upper()}"


class Order(Timestamped):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT"
        PAYMENT_SUBMITTED = "PAYMENT_SUBMITTED"
        CONFIRMED = "CONFIRMED"
        PROCESSING = "PROCESSING"
        SHIPPED = "SHIPPED"
        DELIVERED = "DELIVERED"
        CANCELLED = "CANCELLED"

    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID"
        PENDING_VERIFICATION = "PENDING_VERIFICATION"
        PAID = "PAID"
        REJECTED = "REJECTED"
        REFUNDED = "REFUNDED"

    order_number = models.CharField(max_length=40, unique=True, default=order_number, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders", null=True, blank=True
    )
    guest_key = models.CharField(max_length=64, blank=True, default="", db_index=True, editable=False)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT, db_index=True
    )
    payment_status = models.CharField(
        max_length=24, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID, db_index=True
    )
    subtotal = money_field()
    discount = money_field(default=0)
    shipping_cost = money_field(default=0)
    total_amount = money_field()
    coupon = models.ForeignKey("promotions.Coupon", on_delete=models.PROTECT, null=True, blank=True)
    customer_name = models.CharField(max_length=160)
    customer_phone = models.CharField(max_length=30)
    shipping_address = models.JSONField()
    customer_note = models.TextField(blank=True)
    admin_note = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    stock_deducted = models.BooleanField(default=False, editable=False)

    class Meta(Timestamped.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    subtotal__gte=0, discount__gte=0, shipping_cost__gte=0, total_amount__gte=0
                ),
                name="order_nonnegative",
            )
        ]

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT)
    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT)
    product_name = models.CharField(max_length=160)
    sku = models.CharField(max_length=80)
    size = models.CharField(max_length=30)
    color = models.CharField(max_length=80)
    category_name = models.CharField(max_length=160)
    quantity = models.PositiveIntegerField()
    unit_price = money_field()
    subtotal = money_field()

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0, unit_price__gte=0, subtotal__gte=0),
                name="valid_order_item",
            )
        ]
