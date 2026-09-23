from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import Address
from cart.services import locked_cart, validate_variant
from catalog.models import Product, ProductVariant
from core.api import Conflict
from core.models import StoreSettings
from payments.models import Payment, StorePaymentSettings
from promotions.models import Coupon
from promotions.services import calculate_discount

from .models import Order, OrderItem


@transaction.atomic
def checkout(
    user, shipping_address_id=None, coupon_code="", customer_note="", guest_address=None, guest_key=""
):
    cart = locked_cart(user, guest_key)
    address = (
        get_object_or_404(Address, pk=shipping_address_id, user=user)
        if user.is_authenticated
        else Address(**(guest_address or {}))
    )
    items = list(cart.items.order_by("variant_id"))
    if not items:
        raise ValidationError("Your cart is empty.")
    store = StoreSettings.objects.filter(active=True).first()
    config = StorePaymentSettings.objects.filter(is_active=True).first()
    if not store or not config:
        raise Conflict("Store and payment settings must be configured before checkout.")
    if store.currency != config.currency:
        raise Conflict("Store and payment currencies must match.")
    variants = {
        v.pk: v
        for v in ProductVariant.objects.select_for_update(of=("self",))
        .select_related("product__category", "size", "color")
        .filter(pk__in=[i.variant_id for i in items])
        .order_by("pk")
    }
    products = {
        p.pk: p
        for p in Product.objects.select_for_update(of=("self",))
        .select_related("category")
        .filter(pk__in=[v.product_id for v in variants.values()])
        .order_by("pk")
    }
    subtotal = Decimal("0")
    for item in items:
        variant = variants[item.variant_id]
        variant.product = products[variant.product_id]
        validate_variant(variant, item.quantity)
        subtotal += variant.effective_price * item.quantity
    coupon = None
    discount = Decimal("0")
    if coupon_code:
        coupon = Coupon.objects.select_for_update().filter(code=coupon_code.strip().upper()).first()
        if not coupon:
            raise ValidationError({"coupon_code": "Unknown coupon."})
        discount = calculate_discount(coupon, subtotal)
        coupon.times_used += 1
        coupon.save(update_fields=["times_used", "updated_at"])
    shipping = store.shipping_fee
    if store.free_shipping_threshold is not None and subtotal - discount >= store.free_shipping_threshold:
        shipping = Decimal("0")
    address_fields = [
        "country",
        "province",
        "district",
        "sector",
        "cell",
        "village",
        "street_or_landmark",
        "additional_information",
    ]
    order = Order.objects.create(
        user=user if user.is_authenticated else None,
        guest_key=guest_key if not user.is_authenticated else "",
        subtotal=subtotal,
        discount=discount,
        shipping_cost=shipping,
        total_amount=subtotal - discount + shipping,
        coupon=coupon,
        customer_name=address.full_name,
        customer_phone=address.phone_number,
        shipping_address={key: getattr(address, key) for key in address_fields},
        customer_note=customer_note,
    )
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                order=order,
                product=variants[item.variant_id].product,
                variant=variants[item.variant_id],
                product_name=variants[item.variant_id].product.name,
                sku=variants[item.variant_id].sku,
                size=variants[item.variant_id].size.name,
                color=variants[item.variant_id].color.name,
                category_name=variants[item.variant_id].product.category.name,
                quantity=item.quantity,
                unit_price=variants[item.variant_id].effective_price,
                subtotal=variants[item.variant_id].effective_price * item.quantity,
            )
            for item in items
        ]
    )
    Payment.objects.create(
        order=order,
        amount=order.total_amount,
        currency=config.currency,
        instructions_snapshot={
            key: getattr(config, key)
            for key in ["merchant_name", "momo_phone_number", "payment_instructions", "currency"]
        },
    )
    cart.items.all().delete()
    return order


@transaction.atomic
def transition_order(order_id, target, admin_note=""):
    order = get_object_or_404(Order.objects.select_for_update(), pk=order_id)
    if target == order.status:
        return order
    transitions = {
        "PENDING_PAYMENT": {"CANCELLED"},
        "PAYMENT_SUBMITTED": {"CANCELLED"},
        "CONFIRMED": {"PROCESSING", "CANCELLED"},
        "PROCESSING": {"SHIPPED", "CANCELLED"},
        "SHIPPED": {"DELIVERED"},
        "DELIVERED": set(),
        "CANCELLED": set(),
    }
    if target not in transitions.get(order.status, set()):
        raise Conflict(f"Cannot change {order.status} to {target}. Confirm orders by verifying payment.")
    if target in {"PROCESSING", "SHIPPED", "DELIVERED"} and order.payment_status != "PAID":
        raise Conflict("Only paid orders may be fulfilled.")
    if target == "CANCELLED":
        if order.payment_status == "PAID":
            raise Conflict(
                "Paid orders cannot be cancelled until a separate, audited refund workflow is implemented."
            )
        if order.coupon_id:
            coupon = Coupon.objects.select_for_update().get(pk=order.coupon_id)
            coupon.times_used = max(0, coupon.times_used - 1)
            coupon.save(update_fields=["times_used", "updated_at"])
    order.status = target
    order.admin_note = admin_note
    timestamp = {"SHIPPED": "shipped_at", "DELIVERED": "delivered_at", "CANCELLED": "cancelled_at"}.get(
        target
    )
    if timestamp:
        setattr(order, timestamp, timezone.now())
    order.save()
    return order
