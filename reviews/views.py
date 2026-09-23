from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny

from core.permissions import IsCustomer

from .models import Review
from .serializers import ReviewSerializer


class ReviewViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ReviewSerializer
    queryset = Review.objects.filter(is_approved=True, product__is_active=True).select_related("user")
    filterset_fields = ["product"]

    def get_permissions(self):
        return [IsCustomer()] if self.action == "create" else [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
