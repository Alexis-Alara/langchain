from slowapi import Limiter
from slowapi.util import get_remote_address


def api_key_or_ip(request):
    return request.headers.get("x-api-key") or get_remote_address(request)


limiter = Limiter(key_func=api_key_or_ip)
