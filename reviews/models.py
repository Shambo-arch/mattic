from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import Timestamped


class Review(Timestamped):
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=160)
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)

    class Meta(Timestamped.Meta):
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_customer_review"),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5), name="review_rating_range"
            ),
        ]
