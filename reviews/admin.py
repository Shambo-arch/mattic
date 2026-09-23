from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "user", "rating", "is_approved", "created_at"]
    list_filter = ["is_approved", "rating"]
    search_fields = ["product__name", "user__email", "title"]
    readonly_fields = ["product", "user", "rating", "title", "comment"]

    def has_add_permission(self, request):
        return False
