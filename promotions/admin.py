from django.contrib import admin

from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ["code", "discount_type", "value", "times_used", "is_active"]
    search_fields = ["code"]
    list_filter = ["is_active", "discount_type"]
    readonly_fields = ["times_used"]
