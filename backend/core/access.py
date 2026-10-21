"""Optional shared demo entrance, independent of workspace ownership and AWS keys."""

import hashlib
import hmac

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle


def gate_version():
    return hashlib.sha256(settings.DEMO_ACCESS_PASSWORD_HASH.encode()).hexdigest()


def access_allowed(request):
    return not settings.DEMO_ACCESS_PASSWORD_HASH or hmac.compare_digest(
        str(request.session.get("demo_access", "")), gate_version()
    )


class AccessThrottle(AnonRateThrottle):
    scope = "demo_access"
    rate = "5/min"
