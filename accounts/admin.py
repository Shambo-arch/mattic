from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import Address, User


class UserCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ["email", "first_name", "last_name", "role"]


class AccountChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = AccountChangeForm
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "role", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    list_filter = ["role", "is_active"]
    readonly_fields = ["date_joined", "last_login", "updated_at", "is_staff"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Profile", {"fields": ["first_name", "last_name", "phone_number"]}),
        (
            "Access",
            {"fields": ["role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions"]},
        ),
        ("Dates", {"fields": ["date_joined", "last_login", "updated_at"]}),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["email", "first_name", "last_name", "role", "password1", "password2"],
            },
        )
    ]

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["full_name", "user", "district", "sector", "is_default"]
    search_fields = ["full_name", "user__email"]
    autocomplete_fields = ["user"]
