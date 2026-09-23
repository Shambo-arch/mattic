import hashlib
import re

from rest_framework.exceptions import PermissionDenied


def guest_key(request):
    """Hash the browser's random bearer secret; never expose it in order data."""
    token = request.headers.get("X-Guest-Token", "")
    if re.fullmatch(r"[0-9a-f]{64}", token):
        return hashlib.sha256(token.encode()).hexdigest()
    return ""


def shopping_owner(user, key=""):
    if user.is_authenticated and user.is_active and user.role == "CUSTOMER":
        return {"user": user}
    if not user.is_authenticated and key:
        return {"user": None, "guest_key": key}
    raise PermissionDenied("A customer account or private guest session is required.")
