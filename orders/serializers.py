from rest_framework import serializers

from accounts.models import Address
from payments.serializers import PaymentSerializer

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        exclude = ["order"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Order
        exclude = ["admin_note", "stock_deducted", "user", "guest_key"]


class DashboardOrderSerializer(OrderSerializer):
    customer_email = serializers.SerializerMethodField()

    def get_customer_email(self, obj) -> str:
        return obj.user.email if obj.user_id else "Guest checkout"

    class Meta:
        model = Order
        exclude = ["guest_key"]


class GuestAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        exclude = ["id", "user", "is_default", "created_at", "updated_at"]


class CheckoutSerializer(serializers.Serializer):
    shipping_address_id = serializers.IntegerField(min_value=1, required=False)
    guest_address = GuestAddressSerializer(required=False)
    coupon_code = serializers.CharField(required=False, allow_blank=True, max_length=50, default="")
    customer_note = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")

    def validate(self, attrs):
        if self.context["request"].user.is_authenticated:
            if "shipping_address_id" not in attrs:
                raise serializers.ValidationError({"shipping_address_id": "Choose your delivery address."})
            attrs.pop("guest_address", None)
        else:
            if "guest_address" not in attrs:
                raise serializers.ValidationError({"guest_address": "Enter your delivery details."})
            attrs.pop("shipping_address_id", None)
        return attrs


class TransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
    admin_note = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")
