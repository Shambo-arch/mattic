from rest_framework.permissions import BasePermission

from .guest import guest_key


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.can_access_dashboard)


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated and request.user.is_active and request.user.role == "CUSTOMER"
        )


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.pk


class IsCustomerOrGuest(IsCustomer):
    def has_permission(self, request, view):
        return super().has_permission(request, view) or (
            not request.user.is_authenticated and bool(guest_key(request))
        )
