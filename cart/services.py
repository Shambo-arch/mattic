from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from accounts.models import User
from catalog.models import ProductVariant
from core.guest import shopping_owner

from .models import Cart, CartItem


def validate_variant(variant, quantity):
    if quantity < 1:
        raise ValidationError({"quantity": "Quantity must be positive."})
    if not (
        variant.is_available
        and variant.product.is_active
        and variant.product.category.is_active
        and variant.size.is_active
        and variant.color.is_active
    ):
        raise ValidationError({"variant": f"{variant.sku} is unavailable."})
    if quantity > variant.stock_quantity:
        raise ValidationError({"quantity": f"Insufficient stock for {variant.sku}."})


def locked_cart(user, guest_key=""):
    owner = shopping_owner(user, guest_key)
    if user.is_authenticated:
        User.objects.select_for_update().get(pk=user.pk)
    cart, _ = Cart.objects.get_or_create(**owner)
    return Cart.objects.select_for_update().get(pk=cart.pk)


@transaction.atomic
def add_item(user, variant_id, quantity, guest_key=""):
    cart = locked_cart(user, guest_key)
    variant = get_object_or_404(
        ProductVariant.objects.select_for_update().select_related("product__category", "size", "color"),
        pk=variant_id,
    )
    item = cart.items.filter(variant=variant).first()
    total = quantity + (item.quantity if item else 0)
    validate_variant(variant, total)
    if item:
        item.quantity = total
        item.save(update_fields=["quantity", "updated_at"])
    else:
        item = CartItem.objects.create(cart=cart, variant=variant, quantity=total)
    return item


@transaction.atomic
def change_item(user, item_id, quantity=None, guest_key=""):
    cart = locked_cart(user, guest_key)
    item = get_object_or_404(cart.items, pk=item_id)
    if quantity is None:
        item.delete()
        return
    variant = (
        ProductVariant.objects.select_for_update()
        .select_related("product__category", "size", "color")
        .get(pk=item.variant_id)
    )
    validate_variant(variant, quantity)
    item.quantity = quantity
    item.save(update_fields=["quantity", "updated_at"])
    return item


@transaction.atomic
def clear_cart(user, guest_key=""):
    locked_cart(user, guest_key).items.all().delete()
