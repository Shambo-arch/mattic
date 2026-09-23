import warnings
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


def image_path(instance, filename):
    return f"{instance._meta.model_name}/{uuid4().hex}{Path(filename).suffix.lower()}"


def validate_image(upload):
    if Path(upload.name).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValidationError("Only JPG, JPEG, PNG and WEBP images are accepted.")
    if upload.size > settings.MAX_UPLOAD_BYTES:
        raise ValidationError("Image must be at most 5 MB.")
    try:
        upload.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as img:
                expected = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
                if (
                    img.format != expected[Path(upload.name).suffix.lower()]
                    or img.width * img.height > 20_000_000
                ):
                    raise ValidationError("Invalid image format or dimensions.")
                img.verify()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise ValidationError("Upload a valid image.")
    finally:
        upload.seek(0)
