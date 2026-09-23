from django.contrib import admin

from core.admin import ReadOnlyAdmin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in OrderItem._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(ReadOnlyAdmin):
    list_display = ["order_number", "user", "status", "payment_status", "total_amount", "created_at"]
    search_fields = ["order_number", "user__email"]
    list_filter = ["status", "payment_status", "created_at"]
    inlines = [OrderItemInline]


admin.site.register(OrderItem, ReadOnlyAdmin)
