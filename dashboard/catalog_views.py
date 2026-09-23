from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets

from catalog.models import Brand, Category, Color, Product, ProductImage, ProductVariant, Size
from catalog.serializers import (
    BrandSerializer,
    CategorySerializer,
    ColorSerializer,
    ProductImageSerializer,
    ProductWriteSerializer,
    SizeSerializer,
    VariantSerializer,
)
from core.models import StoreSettings
from core.permissions import IsAdminRole
from core.serializers import StoreSettingsSerializer
from payments.models import StorePaymentSettings
from payments.serializers import PaymentSettingsSerializer
from promotions.models import Coupon

from .filters import InventoryFilter
from .serializers import CouponSerializer


class AdminModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        get_object_or_404(self.queryset.model.objects.select_for_update(), pk=kwargs["pk"])
        return super().update(request, *args, **kwargs)


class ProductAdminViewSet(AdminModelViewSet):
    queryset = Product.objects.select_related("category", "brand")
    serializer_class = ProductWriteSerializer
    filterset_fields = ["category", "brand", "is_active", "featured"]
    search_fields = ["name", "slug"]


class CategoryAdminViewSet(AdminModelViewSet):
    queryset = Category.objects.select_related("parent")
    serializer_class = CategorySerializer
    search_fields = ["name"]


class BrandAdminViewSet(AdminModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    search_fields = ["name"]


class ColorAdminViewSet(AdminModelViewSet):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer


class SizeAdminViewSet(AdminModelViewSet):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer


class VariantAdminViewSet(AdminModelViewSet):
    queryset = ProductVariant.objects.select_related("product", "size", "color")
    serializer_class = VariantSerializer
    filterset_class = InventoryFilter
    search_fields = ["sku", "product__name", "size__name", "color__name"]


class ImageAdminViewSet(AdminModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    filterset_fields = ["product"]

    @transaction.atomic
    def save_image(self, serializer):
        product = serializer.validated_data.get("product") or serializer.instance.product
        Product.objects.select_for_update().get(pk=product.pk)
        if serializer.validated_data.get("is_primary"):
            ProductImage.objects.filter(product=product).update(is_primary=False)
        serializer.save()

    perform_create = save_image
    perform_update = save_image


class CouponAdminViewSet(AdminModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    search_fields = ["code"]
    filterset_fields = ["is_active", "discount_type"]


class StoreSettingsAdminViewSet(AdminModelViewSet):
    queryset = StoreSettings.objects.all()
    serializer_class = StoreSettingsSerializer


class PaymentSettingsAdminViewSet(AdminModelViewSet):
    queryset = StorePaymentSettings.objects.all()
    serializer_class = PaymentSettingsSerializer
