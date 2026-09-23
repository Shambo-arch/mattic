from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig


class OwnerAdminSite(AdminSite):
    def has_permission(self, request):
        return bool(
            request.user.is_authenticated and request.user.is_staff and request.user.can_access_dashboard
        )


class OwnerAdminConfig(AdminConfig):
    default_site = "core.admin_site.OwnerAdminSite"
