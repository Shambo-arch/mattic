from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response

from core.guest import guest_key, shopping_owner
from core.permissions import IsCustomerOrGuest

from .models import Cart, CartItem
from .serializers import AddCartItemSerializer, CartItemSerializer, CartSerializer, UpdateCartItemSerializer
from .services import add_item, change_item, clear_cart


class CartView(generics.GenericAPIView):
    permission_classes = [IsCustomerOrGuest]
    serializer_class = CartSerializer

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(**shopping_owner(request.user, guest_key(request)))
        cart = Cart.objects.prefetch_related(
            Prefetch(
                "items",
                queryset=CartItem.objects.select_related(
                    "variant__product", "variant__size", "variant__color"
                ),
            )
        ).get(pk=cart.pk)
        return Response(self.get_serializer(cart).data)


class CartAddView(generics.GenericAPIView):
    permission_classes = [IsCustomerOrGuest]
    serializer_class = AddCartItemSerializer

    @extend_schema(responses={201: CartItemSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = add_item(
            request.user,
            serializer.validated_data["variant"],
            serializer.validated_data["quantity"],
            guest_key=guest_key(request),
        )
        return Response(CartItemSerializer(item).data, status=201)


class CartItemView(generics.GenericAPIView):
    permission_classes = [IsCustomerOrGuest]
    serializer_class = UpdateCartItemSerializer

    @extend_schema(responses=CartItemSerializer)
    def patch(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = change_item(
            request.user, pk, serializer.validated_data["quantity"], guest_key=guest_key(request)
        )
        return Response(CartItemSerializer(item).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        change_item(request.user, pk, guest_key=guest_key(request))
        return Response(status=204)


class CartClearView(generics.GenericAPIView):
    permission_classes = [IsCustomerOrGuest]
    serializer_class = CartSerializer

    @extend_schema(responses={204: None})
    def delete(self, request):
        clear_cart(request.user, guest_key=guest_key(request))
        return Response(status=204)
