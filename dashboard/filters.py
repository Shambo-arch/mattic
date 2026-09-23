import django_filters

from catalog.models import ProductVariant
from core.models import StoreSettings
from orders.models import Order
from payments.models import Payment


class OrderFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    customer = django_filters.NumberFilter(field_name="user_id")

    class Meta:
        model = Order
        fields = ["status", "payment_status", "order_number"]


class PaymentFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="submitted_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="submitted_at", lookup_expr="date__lte")

    class Meta:
        model = Payment
        fields = ["status", "order"]


class InventoryFilter(django_filters.FilterSet):
    low_stock = django_filters.BooleanFilter(method="filter_low")
    out_of_stock = django_filters.BooleanFilter(method="filter_out")
    variant = django_filters.NumberFilter(field_name="pk")

    class Meta:
        model = ProductVariant
        fields = ["product", "is_available"]

    def filter_low(self, queryset, name, value):
        store = StoreSettings.objects.filter(active=True).first()
        threshold = store.low_stock_threshold if store else 5
        low = queryset.filter(stock_quantity__gt=0, stock_quantity__lte=threshold)
        return low if value else queryset.exclude(pk__in=low.values("pk"))

    def filter_out(self, queryset, name, value):
        return queryset.filter(stock_quantity=0) if value else queryset.filter(stock_quantity__gt=0)
