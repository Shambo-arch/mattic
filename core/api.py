from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.renderers import JSONRenderer


class Conflict(APIException):
    status_code = 409
    default_detail = "This action conflicts with the current state."


def exception_handler(exc, context):
    from rest_framework.views import exception_handler as drf_exception_handler

    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(getattr(exc, "message_dict", exc.messages))
    if isinstance(exc, (ProtectedError, IntegrityError)):
        exc = Conflict("Related records or a uniqueness constraint prevent this change.")
    return drf_exception_handler(exc, context)


class EnvelopeRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = (renderer_context or {}).get("response")
        if response and response.status_code == 204:
            return b""
        success = response is None or response.status_code < 400
        payload = {
            "success": success,
            "message": "Request successful." if success else "Request failed.",
            "data" if success else "errors": data,
        }
        return super().render(decimal_strings(payload), accepted_media_type, renderer_context)


def decimal_strings(value):
    if isinstance(value, Decimal):
        return format(value, ".2f")
    if isinstance(value, dict):
        return {key: decimal_strings(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [decimal_strings(item) for item in value]
    return value
