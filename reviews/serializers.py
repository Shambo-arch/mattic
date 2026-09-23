from rest_framework import serializers

from orders.models import OrderItem

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="user.first_name", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "product", "rating", "title", "comment", "customer_name", "is_approved", "created_at"]
        read_only_fields = ["id", "customer_name", "is_approved", "created_at"]

    def validate(self, attrs):
        user = self.context["request"].user
        product = attrs["product"]
        if (
            not product.is_active
            or not OrderItem.objects.filter(
                order__user=user, order__status="DELIVERED", product=product
            ).exists()
        ):
            raise serializers.ValidationError("Only delivered purchasers can review this product.")
        if Review.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError("You have already reviewed this product.")
        return attrs


class ReviewModerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "product", "user", "rating", "title", "comment", "is_approved", "created_at"]
        read_only_fields = ["id", "product", "user", "rating", "title", "comment", "created_at"]
