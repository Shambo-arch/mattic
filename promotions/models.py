from django.core.exceptions import ValidationError
from django.db import models

from core.models import Timestamped, money_field


class Coupon(Timestamped):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "PERCENTAGE"
        FIXED = "FIXED"

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices)
    value = money_field()
    minimum_order = money_field(default=0)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0, editable=False)
    is_active = models.BooleanField(default=True)

    class Meta(Timestamped.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(value__gte=0, minimum_order__gte=0), name="coupon_nonnegative"
            ),
            models.CheckConstraint(
                condition=models.Q(end_date__gt=models.F("start_date")), name="coupon_dates"
            ),
            models.CheckConstraint(
                condition=~models.Q(discount_type="PERCENTAGE") | models.Q(value__lte=100),
                name="coupon_percentage",
            ),
            models.CheckConstraint(
                condition=models.Q(usage_limit__isnull=True)
                | models.Q(times_used__lte=models.F("usage_limit")),
                name="coupon_usage",
            ),
        ]

    def clean(self):
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError({"end_date": "End date must follow start date."})
        if self.discount_type == "PERCENTAGE" and self.value is not None and self.value > 100:
            raise ValidationError({"value": "Percentage cannot exceed 100."})
        if self.usage_limit is not None and self.times_used > self.usage_limit:
            raise ValidationError({"usage_limit": "Limit cannot be below existing uses."})

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)
