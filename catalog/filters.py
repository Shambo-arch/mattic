import django_filters
from django.db.models import Exists, OuterRef
from django.db.models.functions import Coalesce

from .models import Category, Product, ProductVariant


class ProductFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(method="filter_category")
    size = django_filters.NumberFilter(method="variant_filter")
    color = django_filters.NumberFilter(method="variant_filter")
    min_price = django_filters.NumberFilter(method="variant_filter", min_value=0)
    max_price = django_filters.NumberFilter(method="variant_filter", min_value=0)
    in_stock = django_filters.BooleanFilter(method="variant_filter")
    best_sellers = django_filters.BooleanFilter(method="filter_best_sellers")

    def filter_best_sellers(self, queryset, name, value):
        return queryset.filter(sold_quantity__gt=0) if value else queryset

    class Meta:
        model = Product
        fields = ["category", "brand", "featured"]

    def filter_category(self, queryset, name, value):
        categories = list(Category.objects.filter(is_active=True).values("id", "slug", "parent_id"))
        ids = {c["id"] for c in categories if str(c["id"]) == value or c["slug"] == value}
        while True:
            expanded = ids | {c["id"] for c in categories if c["parent_id"] in ids}
            if expanded == ids:
                break
            ids = expanded
        return queryset.filter(category_id__in=ids)

    def variant_filter(self, queryset, name, value):
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        values = self.form.cleaned_data
        variants = ProductVariant.objects.filter(
            product=OuterRef("pk"), is_available=True, size__is_active=True, color__is_active=True
        )
        for field in ["size", "color"]:
            if values.get(field) is not None:
                variants = variants.filter(**{f"{field}_id": values[field]})
        variants = variants.annotate(
            effective=Coalesce("price", "product__sale_price", "product__base_price")
        )
        if values.get("min_price") is not None:
            variants = variants.filter(effective__gte=values["min_price"])
        if values.get("max_price") is not None:
            variants = variants.filter(effective__lte=values["max_price"])
        if values.get("in_stock") is not None:
            available = variants.filter(stock_quantity__gt=0)
            queryset = queryset.filter(Exists(available) if values["in_stock"] else ~Exists(available))
        if any(values.get(key) is not None for key in ["size", "color", "min_price", "max_price"]):
            queryset = queryset.filter(Exists(variants))
        return queryset
