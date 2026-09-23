from decimal import Decimal

from rest_framework import serializers

from catalog.serializers import VariantSerializer

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    variant = VariantSerializer(read_only=True)
    unit_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "variant", "quantity", "unit_price", "subtotal"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "subtotal", "total_quantity"]

    def get_subtotal(self, obj) -> Decimal:
        return sum((item.subtotal for item in obj.items.all()), Decimal("0"))

    def get_total_quantity(self, obj) -> int:
        return sum(item.quantity for item in obj.items.all())


class AddCartItemSerializer(serializers.Serializer):
    variant = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=10000)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=10000)
