from decimal import Decimal

from django.db.models import Count, Q, Sum
from drf_spectacular.utils import extend_schema
from rest_framework import generics, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import User
from core.permissions import IsAdminRole
from core.serializers import NoteSerializer
from orders.models import Order
from orders.serializers import DashboardOrderSerializer, TransitionSerializer
from orders.services import transition_order
from payments.models import Payment
from payments.serializers import DashboardPaymentSerializer
from payments.services import reject_payment, verify_payment
from reviews.models import Review
from reviews.serializers import ReviewModerationSerializer

from .filters import OrderFilter, PaymentFilter
from .reports import sales_report, summary
from .serializers import (
    CustomerDetailSerializer,
    CustomerSerializer,
    ReportQuerySerializer,
    SalesReportSerializer,
    SummarySerializer,
)


class OrderAdminViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Order.objects.select_related("payment", "user").prefetch_related("items")
    serializer_class = DashboardOrderSerializer
    filterset_class = OrderFilter
    search_fields = ["order_number", "user__email", "customer_name"]

    @extend_schema(request=TransitionSerializer, responses=DashboardOrderSerializer)
    @action(detail=True, methods=["post", "patch"])
    def transition(self, request, pk=None):
        self.get_object()
        serializer = TransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = transition_order(
            pk, serializer.validated_data["status"], serializer.validated_data["admin_note"]
        )
        return Response(self.get_serializer(order).data)


class PaymentAdminViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Payment.objects.select_related("order__user")
    serializer_class = DashboardPaymentSerializer
    filterset_class = PaymentFilter
    search_fields = ["order__order_number", "transaction_reference", "order__user__email"]

    @extend_schema(request=NoteSerializer, responses=DashboardPaymentSerializer)
    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        self.get_object()
        serializer = NoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = verify_payment(pk, request.user, **serializer.validated_data)
        return Response(self.get_serializer(payment).data)

    @extend_schema(request=NoteSerializer, responses=DashboardPaymentSerializer)
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        self.get_object()
        serializer = NoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = reject_payment(pk, **serializer.validated_data)
        return Response(self.get_serializer(payment).data)


class ReviewAdminViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminRole]
    queryset = Review.objects.select_related("user", "product")
    serializer_class = ReviewModerationSerializer
    filterset_fields = ["is_approved", "product"]


class CustomerAdminViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = (
        User.objects.filter(role="CUSTOMER")
        .annotate(
            number_of_orders=Count("orders"),
            total_spent=Sum(
                "orders__total_amount",
                filter=Q(orders__payment_status="PAID", orders__payment__status="VERIFIED")
                & ~Q(orders__status="CANCELLED"),
                default=Decimal("0"),
            ),
        )
        .order_by("-date_joined")
    )
    serializer_class = CustomerSerializer
    search_fields = ["email", "first_name", "last_name", "phone_number"]

    def get_serializer_class(self):
        return CustomerDetailSerializer if self.action == "retrieve" else CustomerSerializer


class SummaryView(generics.GenericAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = SummarySerializer

    def get(self, request):
        return Response(self.get_serializer(summary()).data)


class SalesReportView(generics.GenericAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = SalesReportSerializer

    @extend_schema(parameters=[ReportQuerySerializer])
    def get(self, request):
        query = ReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return Response(self.get_serializer(sales_report(query.validated_data)).data)
