import logging

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class SafeErrorMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if request.path.startswith("/api/"):
            logger.error("Unhandled API error: %s", type(exception).__name__)
            return JsonResponse(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "The request could not be completed. Please retry or check service health.",
                    }
                },
                status=500,
            )
