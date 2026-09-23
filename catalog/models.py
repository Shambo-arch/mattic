from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from core.models import Named, Timestamped, money_field
from core.uploads import image_path, validate_image


class Category(Named):
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=image_path, validators=[validate_image], blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children"
    )

    def clean(self):
        seen = {self.pk} if self.pk else set()
        parent = self.parent if self.parent_id else None
        while parent:
            if parent.pk in seen:
                raise ValidationError({"parent": "Category hierarchy cannot contain cycles."})
            seen.add(parent.pk)
            parent = parent.parent


class Brand(Named):
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to=image_path, validators=[validate_image], blank=True)


class Color(Timestamped):
    name = models.CharField(max_length=80, unique=True)
    hex_code = models.CharField(
        max_length=7, validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$", "Use a color such as #FFFFFF.")]
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Size(models.Model):
    name = models.CharField(max_length=30)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, null=True, blank=True, related_name="sizes"
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["name", "category"], name="unique_category_size"),
            models.UniqueConstraint(
                fields=["name"], condition=models.Q(category__isnull=True), name="unique_generic_size"
            ),
        ]

    def __str__(self):
        return self.name


class Product(Named):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    short_description = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    material = models.CharField(max_length=160, blank=True)
    base_price = money_field()
    sale_price = money_field(null=True, blank=True)
    featured = models.BooleanField(default=False)

    class Meta(Named.Meta):
        abstract = False
        constraints = [
            models.CheckConstraint(condition=models.Q(base_price__gte=0), name="product_price_nonnegative"),
            models.CheckConstraint(
                condition=models.Q(sale_price__isnull=True)
                | models.Q(sale_price__gte=0, sale_price__lte=models.F("base_price")),
                name="product_valid_sale",
            ),
        ]
        indexes = [models.Index(fields=["is_active", "featured", "-created_at"])]

    @property
    def current_price(self):
        return self.sale_price if self.sale_price is not None else self.base_price

    def clean(self):
        if self.sale_price is not None and self.base_price is not None and self.sale_price > self.base_price:
            raise ValidationError({"sale_price": "Sale price cannot exceed base price."})


class ProductImage(Timestamped):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=image_path, validators=[validate_image])
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["product"], condition=models.Q(is_primary=True), name="one_primary_image"
            )
        ]


class ProductVariant(Timestamped):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    size = models.ForeignKey(Size, on_delete=models.PROTECT)
    color = models.ForeignKey(Color, on_delete=models.PROTECT)
    sku = models.CharField(max_length=80, unique=True)
    price = money_field(null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)

    class Meta(Timestamped.Meta):
        constraints = [
            models.UniqueConstraint(fields=["product", "size", "color"], name="unique_product_variant"),
            models.CheckConstraint(condition=models.Q(stock_quantity__gte=0), name="stock_nonnegative"),
            models.CheckConstraint(
                condition=models.Q(price__isnull=True) | models.Q(price__gte=0),
                name="variant_price_nonnegative",
            ),
        ]

    @property
    def effective_price(self):
        return self.price if self.price is not None else self.product.current_price

    def __str__(self):
        return self.sku
