from drf_spectacular.utils import extend_schema
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from core.guest import guest_key, shopping_owner
from core.permissions import IsCustomerOrGuest
from payments.serializers import PaymentProofSerializer
from payments.services import submit_proof

from .models import Order
from .serializers import CheckoutSerializer, OrderSerializer
from .services import checkout


class CheckoutView(generics.GenericAPIView):
    permission_classes = [IsCustomerOrGuest]
    serializer_class = CheckoutSerializer

    @extend_schema(responses={201: OrderSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = checkout(request.user, guest_key=guest_key(request), **serializer.validated_data)
        return Response(OrderSerializer(order, context={"request": request}).data, status=201)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsCustomerOrGuest]
    serializer_class = OrderSerializer
    filterset_fields = ["status", "payment_status"]

    def get_queryset(self):
        if not self.request.user.is_authenticated and not guest_key(self.request):
            return Order.objects.none()
        return (
            Order.objects.filter(**shopping_owner(self.request.user, guest_key(self.request)))
            .select_related("payment")
            .prefetch_related("items")
        )

    @extend_schema(
        request=PaymentProofSerializer,
        responses=OrderSerializer,
        description="Upload JPG, PNG or WEBP, at most 5 MB. Rejected payments may be resubmitted.",
    )
    @action(
        detail=True, methods=["post"], url_path="payment-proof", parser_classes=[MultiPartParser, FormParser]
    )
    def payment_proof(self, request, pk=None):
        self.get_object()
        serializer = PaymentProofSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = submit_proof(request.user, pk, guest_key=guest_key(request), **serializer.validated_data)
        return Response(self.get_serializer(order).data)
