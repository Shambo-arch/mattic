"""
URL configuration for mattic_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from accounts.views import AddressViewSet, LoginView, LogoutView, MeView, RefreshView, RegisterView
from cart.views import CartAddView, CartClearView, CartItemView, CartView
from catalog.views import BrandViewSet, CategoryViewSet, ColorViewSet, ProductViewSet, SizeViewSet
from core.views import PaymentInstructionsView, StoreView
from dashboard.catalog_views import (
    BrandAdminViewSet,
    CategoryAdminViewSet,
    ColorAdminViewSet,
    CouponAdminViewSet,
    ImageAdminViewSet,
    PaymentSettingsAdminViewSet,
    ProductAdminViewSet,
    SizeAdminViewSet,
    StoreSettingsAdminViewSet,
    VariantAdminViewSet,
)
from dashboard.views import (
    CustomerAdminViewSet,
    OrderAdminViewSet,
    PaymentAdminViewSet,
    ReviewAdminViewSet,
    SalesReportView,
    SummaryView,
)
from orders.views import CheckoutView, OrderViewSet
from payments.views import ScreenshotView
from reviews.views import ReviewViewSet
from wishlist.views import WishlistAddView, WishlistItemView, WishlistView

router = DefaultRouter()
for prefix, viewset, basename in [
    ("products", ProductViewSet, "product"),
    ("categories", CategoryViewSet, "category"),
    ("brands", BrandViewSet, "brand"),
    ("colors", ColorViewSet, "color"),
    ("sizes", SizeViewSet, "size"),
    ("addresses", AddressViewSet, "address"),
    ("orders", OrderViewSet, "order"),
    ("reviews", ReviewViewSet, "review"),
]:
    router.register(prefix, viewset, basename=basename)

dashboard_router = DefaultRouter()
for prefix, viewset in [
    ("products", ProductAdminViewSet),
    ("categories", CategoryAdminViewSet),
    ("brands", BrandAdminViewSet),
    ("colors", ColorAdminViewSet),
    ("sizes", SizeAdminViewSet),
    ("images", ImageAdminViewSet),
    ("variants", VariantAdminViewSet),
    ("inventory", VariantAdminViewSet),
    ("coupons", CouponAdminViewSet),
    ("orders", OrderAdminViewSet),
    ("payments", PaymentAdminViewSet),
    ("customers", CustomerAdminViewSet),
    ("reviews", ReviewAdminViewSet),
    ("settings", StoreSettingsAdminViewSet),
    ("payment-settings", PaymentSettingsAdminViewSet),
]:
    dashboard_router.register(prefix, viewset, basename=f"dashboard-{prefix}")

urlpatterns = [
    path("healthz/", lambda request: JsonResponse({"status": "ok"})),
    path("django-admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/v1/auth/register/", RegisterView.as_view()),
    path("api/v1/auth/login/", LoginView.as_view()),
    path("api/v1/auth/token/refresh/", RefreshView.as_view()),
    path("api/v1/auth/logout/", LogoutView.as_view()),
    path("api/v1/auth/me/", MeView.as_view()),
    path("api/v1/cart/", CartView.as_view()),
    path("api/v1/cart/items/", CartAddView.as_view()),
    path("api/v1/cart/items/<int:pk>/", CartItemView.as_view()),
    path("api/v1/cart/clear/", CartClearView.as_view()),
    path("api/v1/wishlist/", WishlistView.as_view()),
    path("api/v1/wishlist/items/", WishlistAddView.as_view()),
    path("api/v1/wishlist/items/<int:pk>/", WishlistItemView.as_view()),
    path("api/v1/checkout/", CheckoutView.as_view()),
    path("api/v1/payments/<int:pk>/screenshot/", ScreenshotView.as_view(), name="payment-screenshot"),
    path("api/v1/store/", StoreView.as_view()),
    path("api/v1/payment-instructions/", PaymentInstructionsView.as_view()),
    path("api/v1/dashboard/summary/", SummaryView.as_view()),
    path("api/v1/dashboard/reports/sales/", SalesReportView.as_view()),
    path("api/v1/dashboard/", include(dashboard_router.urls)),
    path("api/v1/", include(router.urls)),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA:
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]

admin.site.site_header = "Suit and Tie Fashion Shop — Internal Administration"
admin.site.site_title = "Suit and Tie Fashion Shop"

handler400 = "core.errors.bad_request"
handler403 = "core.errors.permission_denied"
handler404 = "core.errors.not_found"
handler500 = "core.errors.server_error"
