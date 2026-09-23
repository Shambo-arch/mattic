from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html
from rest_framework.exceptions import APIException

from core.admin import ReadOnlyAdmin

from .models import Payment, StorePaymentSettings
from .services import reject_payment, verify_payment


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = ["order", "amount", "currency", "status", "submitted_at", "verified_at"]
    search_fields = ["order__order_number", "transaction_reference"]
    list_filter = ["status", "submitted_at"]
    exclude = ["screenshot"]
    actions = ["verify", "reject"]
    readonly_fields = ["payment_proof"]

    @admin.display(description="Payment screenshot")
    def payment_proof(self, obj):
        if not obj.screenshot:
            return "No proof submitted"
        return format_html(
            '<a href="{}">View payment screenshot</a>', reverse("admin:payments_payment_proof", args=[obj.pk])
        )

    def get_urls(self):
        return [
            path(
                "<int:payment_id>/proof/",
                self.admin_site.admin_view(self.proof),
                name="payments_payment_proof",
            )
        ] + super().get_urls()

    def proof(self, request, payment_id):
        payment = get_object_or_404(Payment, pk=payment_id)
        if not request.user.can_access_dashboard or not self.has_view_permission(request, payment):
            return HttpResponseForbidden()
        if not payment.screenshot:
            from django.http import Http404

            raise Http404
        response = FileResponse(payment.screenshot.open("rb"))
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @admin.action(description="Verify submitted payments (deduct stock once)")
    def verify(self, request, queryset):
        for payment in queryset:
            try:
                verify_payment(payment.pk, request.user, "Verified through internal Django Admin.")
            except (APIException, ValidationError) as exc:
                self.message_user(request, str(exc), level=messages.ERROR)

    @admin.action(description="Reject submitted payments")
    def reject(self, request, queryset):
        for payment in queryset:
            try:
                reject_payment(payment.pk, "Rejected through internal Django Admin.")
            except (APIException, ValidationError) as exc:
                self.message_user(request, str(exc), level=messages.ERROR)


@admin.register(StorePaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ["merchant_name", "momo_phone_number", "currency", "is_active"]
    exclude = ["momo_code"]
