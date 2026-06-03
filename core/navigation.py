from django.utils.http import url_has_allowed_host_and_scheme


def get_safe_return_url(request, fallback_url):
    next_url = request.GET.get("next", "").strip()
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return fallback_url
