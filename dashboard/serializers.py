from rest_framework import serializers

from accounts.serializers import UserSerializer
from core.serializers import ValidatedModelSerializer
from orders.serializers import DashboardOrderSerializer
from promotions.models import Coupon


class CouponSerializer(ValidatedModelSerializer):
    class Meta:
        model = Coupon
        fields = "__all__"
        read_only_fields = ["times_used"]

    def validate_code(self, value):
        code = value.strip().upper()
        queryset = Coupon.objects.filter(code=code)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Coupon code already exists.")
        return code


class CustomerSerializer(UserSerializer):
    number_of_orders = serializers.IntegerField(read_only=True)
    total_spent = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["number_of_orders", "total_spent", "is_active"]


class CustomerDetailSerializer(CustomerSerializer):
    recent_orders = serializers.SerializerMethodField()

    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields + ["recent_orders"]

    def get_recent_orders(self, obj) -> list[dict]:
        orders = obj.orders.select_related("payment", "user").prefetch_related("items")[:10]
        return DashboardOrderSerializer(orders, many=True, context=self.context).data


class ReportQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        if attrs.get("date_from") and attrs.get("date_to") and attrs["date_from"] > attrs["date_to"]:
            raise serializers.ValidationError("date_from must not follow date_to.")
        return attrs


class SalesReportSerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=18, decimal_places=2)
    paid_orders = serializers.IntegerField()
    average_order_value = serializers.DecimalField(max_digits=18, decimal_places=2)
    best_selling_products = serializers.ListField(child=serializers.DictField())
    best_selling_categories = serializers.ListField(child=serializers.DictField())
    recent_sales_trend = serializers.ListField(child=serializers.DictField())
    new_customers = serializers.IntegerField()
    delivered_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()


class SummarySerializer(serializers.Serializer):
    total_sales = serializers.DecimalField(max_digits=18, decimal_places=2)
    today_sales = serializers.DecimalField(max_digits=18, decimal_places=2)
    orders_today = serializers.IntegerField()
    total_customers = serializers.IntegerField()
    total_products = serializers.IntegerField()
    pending_payment_verifications = serializers.IntegerField()
    processing_orders = serializers.IntegerField()
    low_stock_products = serializers.IntegerField()
    out_of_stock_variants = serializers.IntegerField()
    recent_orders = DashboardOrderSerializer(many=True)
    top_selling_products = serializers.ListField(child=serializers.DictField())
