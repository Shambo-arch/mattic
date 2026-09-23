from django.urls import reverse
from rest_framework import serializers

from core.serializers import ValidatedModelSerializer
from core.uploads import validate_image

from .models import Payment, StorePaymentSettings


class PaymentSettingsSerializer(ValidatedModelSerializer):
    class Meta:
        model = StorePaymentSettings
        exclude = ["momo_code"]


class PaymentSerializer(serializers.ModelSerializer):
    screenshot_url = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "payment_method",
            "amount",
            "currency",
            "instructions_snapshot",
            "transaction_reference",
            "screenshot_url",
            "status",
            "admin_note",
            "submitted_at",
            "verified_at",
            "rejected_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_screenshot_url(self, obj) -> str | None:
        if not obj.screenshot:
            return None
        path = reverse("payment-screenshot", args=[obj.pk])
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path


class DashboardPaymentSerializer(PaymentSerializer):
    customer = serializers.SerializerMethodField()

    def get_customer(self, obj) -> str:
        return obj.order.user.email if obj.order.user_id else f"Guest: {obj.order.customer_name}"

    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta(PaymentSerializer.Meta):
        fields = PaymentSerializer.Meta.fields + ["customer", "order_number", "verified_by"]
        read_only_fields = fields


class PaymentProofSerializer(serializers.Serializer):
    screenshot = serializers.ImageField(validators=[validate_image])
    transaction_reference = serializers.CharField(
        required=False, allow_blank=True, max_length=120, default=""
    )
