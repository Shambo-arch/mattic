from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError


def calculate_discount(coupon, subtotal):
    now = timezone.now()
    if not coupon.is_active or not coupon.start_date <= now <= coupon.end_date:
        raise ValidationError({"coupon_code": "Coupon is inactive or outside its validity dates."})
    if coupon.usage_limit is not None and coupon.times_used >= coupon.usage_limit:
        raise ValidationError({"coupon_code": "Coupon usage limit reached."})
    if subtotal < coupon.minimum_order:
        raise ValidationError({"coupon_code": "Order does not meet the minimum amount."})
    discount = (
        subtotal * coupon.value / Decimal("100") if coupon.discount_type == "PERCENTAGE" else coupon.value
    )
    return min(subtotal, discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
