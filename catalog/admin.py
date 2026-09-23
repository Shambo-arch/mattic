from django.contrib import admin
from django.utils.html import format_html

from core.admin import ReadOnlyAdmin

from .models import Brand, Category, Color, Product, ProductImage, ProductVariant, Size


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "base_price", "sale_price", "is_active", "featured"]
    search_fields = ["name", "slug"]
    list_filter = ["is_active", "featured", "category"]
    autocomplete_fields = ["category", "brand"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Category, Brand)
class NamedAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active"]
    search_fields = ["name"]


@admin.register(Color, Size)
class ReferenceAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    search_fields = ["name"]


@admin.register(ProductVariant)
class VariantAdmin(ReadOnlyAdmin):
    list_display = ["sku", "product", "size", "color", "stock_quantity", "is_available"]
    search_fields = ["sku", "product__name"]
    list_filter = ["is_available", "size", "color"]


@admin.register(ProductImage)
class ImageAdmin(admin.ModelAdmin):
    list_display = ["product", "thumbnail", "is_primary", "sort_order"]
    autocomplete_fields = ["product"]

    @admin.display(description="Preview")
    def thumbnail(self, obj):
        return format_html('<img src="{}" width="60" alt="">', obj.image.url) if obj.image else ""
