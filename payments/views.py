import mimetypes
from pathlib import Path

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from core.guest import guest_key, shopping_owner
from core.permissions import IsCustomerOrGuest

from .models import Payment
from .serializers import PaymentSerializer


class ScreenshotView(generics.GenericAPIView):
    permission_classes = [IsCustomerOrGuest | IsAuthenticated]
    serializer_class = PaymentSerializer

    @extend_schema(
        responses={(200, "image/png"): OpenApiTypes.BINARY},
        description="Private customer/guest owner or admin download. Supply account or guest credentials and fetch as a blob.",
    )
    def get(self, request, pk):
        queryset = Payment.objects.all()
        if not getattr(request.user, "can_access_dashboard", False):
            owner = (
                {"user": request.user}
                if request.user.is_authenticated
                else shopping_owner(request.user, guest_key(request))
            )
            queryset = queryset.filter(**{f"order__{key}": value for key, value in owner.items()})
        payment = get_object_or_404(queryset, pk=pk)
        if not payment.screenshot:
            from rest_framework.exceptions import NotFound

            raise NotFound("No screenshot has been submitted.")
        response = FileResponse(
            payment.screenshot.open("rb"),
            content_type=mimetypes.guess_type(payment.screenshot.name)[0],
            as_attachment=True,
            filename=f"payment-{payment.pk}{Path(payment.screenshot.name).suffix}",
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
