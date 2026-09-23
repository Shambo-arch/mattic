from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response

from accounts.models import User
from core.permissions import IsCustomer

from .models import Wishlist, WishlistItem
from .serializers import AddWishlistSerializer, WishlistItemSerializer, WishlistSerializer


class WishlistView(generics.GenericAPIView):
    permission_classes = [IsCustomer]
    serializer_class = WishlistSerializer

    def get(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        wishlist = Wishlist.objects.prefetch_related("items__product").get(pk=wishlist.pk)
        return Response(self.get_serializer(wishlist).data)


class WishlistAddView(generics.GenericAPIView):
    permission_classes = [IsCustomer]
    serializer_class = AddWishlistSerializer

    @extend_schema(responses={200: WishlistItemSerializer, 201: WishlistItemSerializer})
    @transaction.atomic
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        User.objects.select_for_update().get(pk=request.user.pk)
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        item, created = WishlistItem.objects.get_or_create(
            wishlist=wishlist, product=serializer.validated_data["product"]
        )
        return Response(WishlistItemSerializer(item).data, status=201 if created else 200)


class WishlistItemView(generics.GenericAPIView):
    permission_classes = [IsCustomer]
    serializer_class = WishlistItemSerializer

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        get_object_or_404(WishlistItem, pk=pk, wishlist__user=request.user).delete()
        return Response(status=204)
