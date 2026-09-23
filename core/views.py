from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import AllowAny

from payments.models import StorePaymentSettings
from payments.serializers import PaymentSettingsSerializer

from .models import StoreSettings
from .serializers import StoreSettingsSerializer


class StoreView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = StoreSettingsSerializer

    def get_object(self):
        return get_object_or_404(StoreSettings, active=True)


class PaymentInstructionsView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PaymentSettingsSerializer

    def get_object(self):
        return get_object_or_404(StorePaymentSettings, is_active=True)
