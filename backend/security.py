"""Middleware: security headers, CSRF origin check, request logging, static caching."""
import logging
import time
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from . import config

log = logging.getLogger("courier.access")

# vis-network (vendored, v9.1.9) injects a fixed set of <style> blocks at runtime. They are allowed by hash so
# style-src does not need 'unsafe-inline'. Re-derive after upgrading vis-network (see static/vendor/README.md).
VIS_STYLE_HASHES = "'sha256-47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=' 'sha256-OutIf5hnp68ctx4ThtV5J02g5HTJ5bbu/hkNfqVXWWo=' 'sha256-4cgFR0//m8/eHo2G/esYsuZetUHlzCUWYM59sfgE9zY=' 'sha256-uepMTym1NwItBa/XV6ef6fQobLL0A0CNVDM5km5L+nQ=' 'sha256-gGUn/VMBXCeWm86qX/pOf+4ZDSbe0JcaXXb4rJjw1mA=' 'sha256-QuPewnJYr+SnQiTnCNHFBw99ExTsz9f8w5320PimEPw=' 'sha256-IY7YKNHjbzQ1NfAKrBZvBZohgXMtxrqB9PaqhAaT3vg=' 'sha256-QE7TOEDW7YIlMzvUUnm8boDWeNBN7PBbaaYJjnp34WI='"
CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-hashes' " + VIS_STYLE_HASHES + "; script-src 'self'; "
       "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
       "form-action 'self'; frame-ancestors 'none'")
HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}
DOCS_CSP = ("default-src 'self'; img-src 'self' data: https://fastapi.tiangolo.com; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; worker-src blob:")
DOCS_PATHS = ("/docs", "/redoc")
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def _host(value: str) -> str:
    return urlparse(value).netloc.lower()


class SecurityMiddleware(BaseHTTPMiddleware):
    """CSRF choice: cookies are SameSite=Lax and every state-changing request must come from the
    same site. We compare the Origin (or Referer) host to the Host header, or to ALLOWED_ORIGINS.
    In production a request with neither header is rejected; in development it is allowed (tests)."""

    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        if request.method in UNSAFE:
            origin = request.headers.get("origin") or request.headers.get("referer")
            if origin:
                allowed = {_host(o) for o in config.ALLOWED_ORIGINS} | {request.headers.get("host", "").lower()}
                if _host(origin) not in allowed:
                    return self._finish(request, JSONResponse(
                        status_code=403, content={"detail": "Cross-site request blocked.", "code": "CSRF"}), start)
            elif config.IS_PROD:
                return self._finish(request, JSONResponse(
                    status_code=403, content={"detail": "Cross-site request blocked.", "code": "CSRF"}), start)
        try:
            response = await call_next(request)
        except Exception:
            log.error("%s %s 500 unhandled", request.method, request.url.path)
            raise
        return self._finish(request, response, start)

    def _finish(self, request, response, start):
        for k, v in HEADERS.items():
            response.headers[k] = v
        if request.url.path.startswith(DOCS_PATHS):   # Swagger/ReDoc (dev only) load their UI from a CDN
            response.headers["Content-Security-Policy"] = DOCS_CSP
        if config.IS_PROD:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        path = request.url.path
        if "cache-control" not in response.headers:
            if path.startswith(("/vendor/", "/img/")):
                response.headers["Cache-Control"] = "public, max-age=86400"
            elif path.startswith(("/css/", "/js/")):
                response.headers["Cache-Control"] = "public, max-age=300, must-revalidate"
            else:
                response.headers["Cache-Control"] = "no-store" if path.startswith("/api/") else "no-cache"
        ms = (time.perf_counter() - start) * 1000
        log.log(logging.WARNING if ms > 1000 else logging.INFO, "%s %s %s %.0fms%s", request.method, path,
                response.status_code, ms, " SLOW" if ms > 1000 else "")
        response.headers["Server-Timing"] = f"app;dur={ms:.0f}"
        return response
