import json
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from rest_framework import serializers

from core.serializers import ValidatedModelSerializer
from core.uploads import validate_image
from reviews.serializers import ReviewSerializer

from .models import Brand, Category, Color, Product, ProductImage, ProductVariant, Size


class CategorySerializer(ValidatedModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class BrandSerializer(ValidatedModelSerializer):
    class Meta:
        model = Brand
        fields = "__all__"


class ColorSerializer(ValidatedModelSerializer):
    class Meta:
        model = Color
        fields = "__all__"


class SizeSerializer(ValidatedModelSerializer):
    class Meta:
        model = Size
        fields = "__all__"


class ProductImageSerializer(ValidatedModelSerializer):
    class Meta:
        model = ProductImage
        fields = "__all__"
        validators = []


class VariantSerializer(ValidatedModelSerializer):
    size_name = serializers.CharField(source="size.name", read_only=True)
    color_name = serializers.CharField(source="color.name", read_only=True)
    effective_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = ProductVariant
        fields = "__all__"

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance and self.instance.orderitem_set.exists():
            for name in ["product", "size", "color", "sku"]:
                if name in attrs and attrs[name] != getattr(self.instance, name):
                    raise serializers.ValidationError(
                        {name: "Variants referenced by orders cannot change identity. Create a new variant."}
                    )
        return attrs


class StockEntrySerializer(serializers.Serializer):
    size_name = serializers.CharField(max_length=30)
    color = serializers.PrimaryKeyRelatedField(queryset=Color.objects.filter(is_active=True))
    stock_quantity = serializers.IntegerField(min_value=0, max_value=2147483647)
    is_available = serializers.BooleanField(default=True)


class ProductWriteSerializer(ValidatedModelSerializer):
    image = serializers.ImageField(required=False, write_only=True, validators=[validate_image])
    new_variants = StockEntrySerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Product
        fields = "__all__"

    def to_internal_value(self, data):
        # Multipart carries the stock rows as JSON alongside the uploaded file.
        if hasattr(data, "getlist"):
            data = {key: data.get(key) for key in data}
            if "new_variants" in data:
                try:
                    data["new_variants"] = json.loads(data["new_variants"])
                except (TypeError, ValueError):
                    raise serializers.ValidationError({"new_variants": "Enter a valid list of stock rows."})
        return super().to_internal_value(data)

    def save_primary_image(self, product, upload):
        if upload is not None:
            Product.objects.select_for_update().get(pk=product.pk)
            product.images.filter(is_primary=True).update(is_primary=False)
            ProductImage.objects.create(
                product=product, image=upload, alt_text=product.name[:255], is_primary=True
            )

    def validate_new_variants(self, rows):
        if len(rows) > 100:
            raise serializers.ValidationError("Add up to 100 size and color combinations at a time.")
        seen = set()
        for row in rows:
            if not {"size_name", "color", "stock_quantity"}.issubset(row):
                raise serializers.ValidationError(
                    "Every new combination needs a size, color and stock quantity."
                )
            key = (row["size_name"].casefold(), row["color"].pk)
            if key in seen:
                raise serializers.ValidationError("Each size and color combination must appear only once.")
            seen.add(key)
        return rows

    def add_stock(self, product, rows):
        for row in rows:
            name = row["size_name"]
            if product.variants.filter(size__name__iexact=name, color=row["color"]).exists():
                raise serializers.ValidationError(
                    {
                        "new_variants": f"Size {name} in {row['color'].name} already exists. Edit its stock instead."
                    }
                )
            size = Size.objects.filter(category=product.category, name__iexact=name).first()
            if size and not size.is_active:
                raise serializers.ValidationError(
                    {"new_variants": f"Activate size {name} before adding stock."}
                )
            if size is None:
                size, _ = Size.objects.get_or_create(category=product.category, name=name)
            ProductVariant.objects.create(
                product=product,
                size=size,
                color=row["color"],
                stock_quantity=row["stock_quantity"],
                is_available=row.get("is_available", True),
                sku=f"ST-{uuid4().hex}",
            )

    @transaction.atomic
    def create(self, validated_data):
        rows = validated_data.pop("new_variants", [])
        upload = validated_data.pop("image", None)
        product = super().create(validated_data)
        self.add_stock(product, rows)
        self.save_primary_image(product, upload)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        rows = validated_data.pop("new_variants", [])
        upload = validated_data.pop("image", None)
        product = super().update(instance, validated_data)
        self.add_stock(product, rows)
        self.save_primary_image(product, upload)
        return product


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = VariantSerializer(source="public_variants", many=True, read_only=True)
    current_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    available_sizes = serializers.SerializerMethodField()
    available_colors = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    reviews = ReviewSerializer(source="approved_reviews", many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    sold_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "brand",
            "short_description",
            "description",
            "material",
            "base_price",
            "sale_price",
            "current_price",
            "featured",
            "images",
            "variants",
            "available_sizes",
            "available_colors",
            "in_stock",
            "reviews",
            "average_rating",
            "review_count",
            "sold_quantity",
            "created_at",
        ]

    def get_available_sizes(self, obj) -> list[dict]:
        return list(
            {
                v.size_id: {"id": v.size_id, "name": v.size.name}
                for v in obj.public_variants
                if v.stock_quantity > 0
            }.values()
        )

    def get_available_colors(self, obj) -> list[dict]:
        return list(
            {
                v.color_id: {"id": v.color_id, "name": v.color.name, "hex_code": v.color.hex_code}
                for v in obj.public_variants
                if v.stock_quantity > 0
            }.values()
        )

    def get_in_stock(self, obj) -> bool:
        return any(v.stock_quantity > 0 for v in obj.public_variants)

    def get_average_rating(self, obj) -> Decimal | None:
        values = obj.approved_reviews
        return round(Decimal(sum(r.rating for r in values)) / len(values), 2) if values else None

    def get_review_count(self, obj) -> int:
        return len(obj.approved_reviews)
