from orders.models import Order
from payments.models import Payment

ORDER_STATUSES = Order.Status.choices
ORDER_PAYMENT_STATUSES = Order.PaymentStatus.choices
PAYMENT_STATUSES = Payment.Status.choices
