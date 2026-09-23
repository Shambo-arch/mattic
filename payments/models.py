from django.conf import settings
from django.db import models

from core.models import Timestamped, money_field
from core.storage import private_storage
from core.uploads import image_path, validate_image


class StorePaymentSettings(Timestamped):
    merchant_name = models.CharField(max_length=160)
    momo_code = models.CharField(max_length=30, blank=True)
    momo_phone_number = models.CharField(max_length=30, default="0784888458")
    payment_instructions = models.TextField()
    currency = models.CharField(max_length=3, default="RWF")
    is_active = models.BooleanField(default=True)

    class Meta(Timestamped.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"], condition=models.Q(is_active=True), name="one_active_payment_settings"
            )
        ]


class Payment(Timestamped):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        SUBMITTED = "SUBMITTED"
        VERIFIED = "VERIFIED"
        REJECTED = "REJECTED"

    order = models.OneToOneField("orders.Order", on_delete=models.PROTECT, related_name="payment")
    payment_method = models.CharField(
        max_length=10, choices=[("MTN_MOMO", "MTN Mobile Money")], default="MTN_MOMO"
    )
    amount = money_field()
    currency = models.CharField(max_length=3, default="RWF")
    instructions_snapshot = models.JSONField(default=dict)
    transaction_reference = models.CharField(max_length=120, blank=True)
    screenshot = models.ImageField(
        storage=private_storage, upload_to=image_path, validators=[validate_image], blank=True
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    admin_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)

    class Meta(Timestamped.Meta):
        constraints = [models.CheckConstraint(condition=models.Q(amount__gte=0), name="payment_nonnegative")]
