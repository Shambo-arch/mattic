from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from core.models import Timestamped


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        user = self.model(email=email.strip().lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.update(role="ADMIN", is_staff=True, is_superuser=True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER"
        ADMIN = "ADMIN"

    username = None
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CUSTOMER)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="user_email_case_insensitive"),
            models.CheckConstraint(
                condition=models.Q(role__in=["CUSTOMER", "ADMIN"]), name="valid_user_role"
            ),
        ]

    @property
    def can_access_dashboard(self):
        return bool(
            self.is_active
            and self.role == self.Role.ADMIN
            and settings.DASHBOARD_ADMIN_EMAIL
            and self.email.strip().lower() == settings.DASHBOARD_ADMIN_EMAIL.strip().lower()
        )

    def validate_admin_email(self):
        if self.role == self.Role.ADMIN and (
            not settings.DASHBOARD_ADMIN_EMAIL
            or self.email.strip().lower() != settings.DASHBOARD_ADMIN_EMAIL.strip().lower()
        ):
            raise ValidationError({"role": "Only the configured store owner can be an administrator."})

    def clean(self):
        super().clean()
        self.validate_admin_email()

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        self.validate_admin_email()
        self.is_staff = self.role == self.Role.ADMIN
        if self.role != self.Role.ADMIN:
            self.is_superuser = False
        super().save(*args, **kwargs)


class Address(Timestamped):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=160)
    phone_number = models.CharField(max_length=30)
    country = models.CharField(max_length=80, default="Rwanda")
    province = models.CharField(max_length=80)
    district = models.CharField(max_length=80)
    sector = models.CharField(max_length=80)
    cell = models.CharField(max_length=80, blank=True)
    village = models.CharField(max_length=80, blank=True)
    street_or_landmark = models.CharField(max_length=255, blank=True)
    additional_information = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    class Meta(Timestamped.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["user"], condition=models.Q(is_default=True), name="one_default_address"
            )
        ]
