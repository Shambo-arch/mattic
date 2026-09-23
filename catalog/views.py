from django.db.models import IntegerField, Min, OuterRef, Prefetch, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from orders.models import OrderItem
from reviews.models import Review

from .filters import ProductFilter
from .models import Brand, Category, Color, Product, ProductVariant, Size
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ColorSerializer,
    ProductSerializer,
    SizeSerializer,
)


def public_products():
    sales = (
        OrderItem.objects.filter(
            product=OuterRef("pk"), order__payment_status="PAID", order__payment__status="VERIFIED"
        )
        .exclude(order__status="CANCELLED")
        .order_by()
        .values("product")
        .annotate(total=Sum("quantity"))
        .values("total")[:1]
    )
    variants = ProductVariant.objects.filter(
        is_available=True, size__is_active=True, color__is_active=True
    ).select_related("size", "color", "product")
    return (
        Product.objects.filter(is_active=True, category__is_active=True)
        .select_related("category", "brand")
        .prefetch_related(
            "images",
            Prefetch("variants", queryset=variants, to_attr="public_variants"),
            Prefetch(
                "reviews",
                queryset=Review.objects.filter(is_approved=True).select_related("user"),
                to_attr="approved_reviews",
            ),
        )
        .annotate(
            sold_quantity=Coalesce(Subquery(sales, output_field=IntegerField()), 0),
            price=Coalesce(
                Min(
                    Coalesce("variants__price", "sale_price", "base_price"),
                    filter=Q(
                        variants__is_available=True,
                        variants__size__is_active=True,
                        variants__color__is_active=True,
                    ),
                ),
                "sale_price",
                "base_price",
            ),
        )
    )


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filterset_class = ProductFilter
    search_fields = ["name", "short_description", "description", "category__name", "brand__name"]
    ordering_fields = ["price", "created_at", "sold_quantity"]
    ordering = ["-created_at", "-pk"]
    lookup_value_regex = "[^/.]+"

    def get_queryset(self):
        return public_products()

    def get_object(self):
        value = self.kwargs["pk"]
        return get_object_or_404(
            self.get_queryset(), **({"pk": int(value)} if value.isdigit() else {"slug": value})
        )


class PublicReferenceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]


class CategoryViewSet(PublicReferenceViewSet):
    queryset = Category.objects.filter(is_active=True).select_related("parent")
    serializer_class = CategorySerializer


class BrandViewSet(PublicReferenceViewSet):
    queryset = Brand.objects.filter(is_active=True)
    serializer_class = BrandSerializer


class ColorViewSet(PublicReferenceViewSet):
    queryset = Color.objects.filter(is_active=True)
    serializer_class = ColorSerializer


class SizeViewSet(PublicReferenceViewSet):
    queryset = Size.objects.filter(is_active=True)
    serializer_class = SizeSerializer
    filterset_fields = ["category"]
