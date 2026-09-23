from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from accounts.models import User
from catalog.models import Product, ProductVariant
from core.models import StoreSettings
from orders.models import Order, OrderItem
from payments.models import Payment


def paid_orders():
    return Order.objects.filter(payment_status="PAID", payment__status="VERIFIED").exclude(status="CANCELLED")


def best_products(orders):
    return list(
        OrderItem.objects.filter(order__in=orders)
        .values("product_id", "product_name")
        .annotate(quantity=Sum("quantity"), gross_item_sales=Sum("subtotal"))
        .order_by("-quantity", "product_id")[:10]
    )


def date_range(queryset, field, dates):
    for key, lookup in [("date_from", "gte"), ("date_to", "lte")]:
        if dates.get(key):
            queryset = queryset.filter(**{f"{field}__date__{lookup}": dates[key]})
    return queryset


def sales_report(dates):
    paid = date_range(paid_orders(), "confirmed_at", dates)
    orders = date_range(Order.objects.all(), "created_at", dates)
    customers = date_range(User.objects.filter(role="CUSTOMER"), "date_joined", dates)
    totals = paid.aggregate(
        total_revenue=Sum("total_amount", default=Decimal("0")),
        paid_orders=Count("id"),
        average_order_value=Avg("total_amount", default=Decimal("0")),
    )
    return {
        **totals,
        "best_selling_products": best_products(paid),
        "best_selling_categories": list(
            OrderItem.objects.filter(order__in=paid)
            .values("category_name")
            .annotate(quantity=Sum("quantity"), gross_item_sales=Sum("subtotal"))
            .order_by("-quantity", "category_name")[:10]
        ),
        "recent_sales_trend": list(
            paid.annotate(date=TruncDate("confirmed_at"))
            .values("date")
            .annotate(revenue=Sum("total_amount"), orders=Count("id"))
            .order_by("date")
        ),
        "new_customers": customers.count(),
        "delivered_orders": orders.filter(status="DELIVERED").count(),
        "cancelled_orders": orders.filter(status="CANCELLED").count(),
    }


def summary():
    today = timezone.localdate()
    store = StoreSettings.objects.filter(active=True).first()
    threshold = store.low_stock_threshold if store else 5
    paid = paid_orders()
    return {
        "total_sales": paid.aggregate(value=Sum("total_amount", default=Decimal("0")))["value"],
        "today_sales": paid.filter(confirmed_at__date=today).aggregate(
            value=Sum("total_amount", default=Decimal("0"))
        )["value"],
        "orders_today": Order.objects.filter(created_at__date=today).count(),
        "total_customers": User.objects.filter(role="CUSTOMER").count(),
        "total_products": Product.objects.count(),
        "pending_payment_verifications": Payment.objects.filter(
            status="SUBMITTED", order__status="PAYMENT_SUBMITTED"
        ).count(),
        "processing_orders": Order.objects.filter(status="PROCESSING").count(),
        "low_stock_products": ProductVariant.objects.filter(
            stock_quantity__gt=0, stock_quantity__lte=threshold
        )
        .values("product_id")
        .distinct()
        .count(),
        "out_of_stock_variants": ProductVariant.objects.filter(stock_quantity=0).count(),
        "recent_orders": Order.objects.select_related("payment", "user").prefetch_related("items")[:10],
        "top_selling_products": best_products(paid),
    }
