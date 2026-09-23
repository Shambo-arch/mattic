from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from cart.services import validate_variant
from catalog.models import ProductVariant
from core.api import Conflict
from core.guest import shopping_owner
from core.uploads import validate_image
from orders.models import Order

from .models import Payment


@transaction.atomic
def submit_proof(user, order_id, screenshot, transaction_reference="", guest_key=""):
    order = get_object_or_404(
        Order.objects.select_for_update(), pk=order_id, **shopping_owner(user, guest_key)
    )
    payment = Payment.objects.select_for_update().get(order=order)
    if order.status not in {"PENDING_PAYMENT", "PAYMENT_SUBMITTED"} or payment.status not in {
        "PENDING",
        "REJECTED",
    }:
        raise Conflict("This order is not eligible for payment submission.")
    validate_image(screenshot)
    previous = payment.screenshot.name
    payment.screenshot = screenshot
    payment.transaction_reference = transaction_reference
    payment.status = "SUBMITTED"
    payment.submitted_at = timezone.now()
    payment.rejected_at = None
    payment.admin_note = ""
    payment.save()
    order.status = "PAYMENT_SUBMITTED"
    order.payment_status = "PENDING_VERIFICATION"
    order.save(update_fields=["status", "payment_status", "updated_at"])
    if previous:
        transaction.on_commit(lambda: payment.screenshot.storage.delete(previous))
    return order


def lock_payment(payment_id):
    order_id = get_object_or_404(Payment.objects.only("order_id"), pk=payment_id).order_id
    order = Order.objects.select_for_update().get(pk=order_id)
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    return order, payment


@transaction.atomic
def verify_payment(payment_id, admin, admin_note=""):
    order, payment = lock_payment(payment_id)
    if payment.status == "VERIFIED":
        return payment
    if payment.status != "SUBMITTED" or order.status != "PAYMENT_SUBMITTED" or order.stock_deducted:
        raise Conflict("Only submitted payments on eligible orders can be verified.")
    if payment.amount != order.total_amount:
        raise Conflict("Payment amount does not match the order total.")
    items = list(order.items.order_by("variant_id"))
    variants = {
        v.pk: v
        for v in ProductVariant.objects.select_for_update(of=("self",))
        .select_related("product__category", "size", "color")
        .filter(pk__in=[i.variant_id for i in items])
        .order_by("pk")
    }
    for item in items:
        variant = variants[item.variant_id]
        validate_variant(variant, item.quantity)
        variant.stock_quantity -= item.quantity
        variant.save(update_fields=["stock_quantity", "updated_at"])
    now = timezone.now()
    payment.status = "VERIFIED"
    payment.verified_at = now
    payment.verified_by = admin
    payment.admin_note = admin_note
    payment.save()
    order.payment_status = "PAID"
    order.status = "CONFIRMED"
    order.stock_deducted = True
    order.confirmed_at = now
    order.save()
    return payment


@transaction.atomic
def reject_payment(payment_id, admin_note=""):
    order, payment = lock_payment(payment_id)
    if payment.status != "SUBMITTED" or order.status != "PAYMENT_SUBMITTED":
        raise Conflict("Only submitted payments on eligible orders can be rejected.")
    payment.status = "REJECTED"
    payment.rejected_at = timezone.now()
    payment.admin_note = admin_note
    payment.save()
    order.payment_status = "REJECTED"
    order.status = "PENDING_PAYMENT"
    order.save(update_fields=["payment_status", "status", "updated_at"])
    return payment
