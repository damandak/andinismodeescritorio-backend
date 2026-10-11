"""Helpers for the security settings (see "Seguridad" in settings.py)."""

LOCAL_PEERS = {"127.0.0.1", "::1", ""}  # "" = unix socket (gunicorn behind nginx)


def client_ip(request):
    """IP address of the visitor, used to limit failed admin logins (django-axes).

    Django sits behind nginx on the same server, so REMOTE_ADDR is nginx itself.
    nginx passes the visitor's address in X-Forwarded-For; with the usual
    `$proxy_add_x_forwarded_for` it *appends* what it saw, so only the last
    entry is trustworthy (anything before it was sent by the visitor and can be
    made up). The header is only read when the request comes from the local
    proxy, never from the internet directly.
    """
    remote = request.META.get("REMOTE_ADDR") or ""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded and remote in LOCAL_PEERS:
        return forwarded.split(",")[-1].strip()
    return remote or None


def https_origins(hosts):
    """https://<host> for each real host name in ALLOWED_HOSTS.

    Used as CSRF_TRUSTED_ORIGINS so the admin login works over HTTPS even if
    the proxy doesn't tell Django the connection was HTTPS.
    """
    origins = []
    for host in hosts:
        host = host.strip().lstrip(".")
        if not host or host == "*" or host in ("localhost", "127.0.0.1", "[::1]"):
            continue
        origins.append(f"https://{host}")
    return origins


def login_username(request, credentials):
    """Account used in a login attempt, for django-axes. The admin form sends
    it as "username", the site's login (allauth) as "email"."""
    credentials = credentials or {}
    value = credentials.get("username") or credentials.get("email")
    if not value and request is not None:
        value = request.POST.get("username") or request.POST.get("email")
    return (value or "").strip().lower() or None
