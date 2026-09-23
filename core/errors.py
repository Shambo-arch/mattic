from django.http import JsonResponse
from django.views import defaults


def api_error(status, message):
    return JsonResponse({"success": False, "message": message, "errors": {"detail": message}}, status=status)


def bad_request(request, exception):
    if request.path.startswith("/api/"):
        return api_error(400, "Invalid request.")
    return defaults.bad_request(request, exception)


def permission_denied(request, exception):
    if request.path.startswith("/api/"):
        return api_error(403, "Permission denied.")
    return defaults.permission_denied(request, exception)


def not_found(request, exception):
    if request.path.startswith("/api/"):
        return api_error(404, "Resource not found.")
    return defaults.page_not_found(request, exception)


def server_error(request):
    if request.path.startswith("/api/"):
        return api_error(500, "An internal error occurred.")
    return defaults.server_error(request)
