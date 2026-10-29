"""Clean-URL HTML pages, server-side access checks, legacy .html redirects and branded error pages."""
from html import escape

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from . import auth, config
from .errors import AppError
from .services.common import require_shipment_access

router = APIRouter(include_in_schema=False)

ERRORS = {
    403: ("Not allowed", "You do not have access to this page."),
    404: ("Page not found", "We could not find what you were looking for."),
    500: ("Something went wrong", "Please try again in a moment."),
}


def error_page(status: int, message: str | None = None) -> HTMLResponse:
    title, default = ERRORS.get(status, ("Error", "Something went wrong."))
    html = (config.PAGES_DIR / "error.html").read_text(encoding="utf-8")
    html = (html.replace("{{code}}", str(status)).replace("{{title}}", escape(title))
                .replace("{{message}}", escape(message or default)))
    return HTMLResponse(html, status_code=status)


def _file(name: str) -> FileResponse:
    return FileResponse(config.PAGES_DIR / name, media_type="text/html")


def _gate(request: Request, name: str, staff: bool = False):
    sess = auth.session(request)
    if not sess:
        nxt = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        return RedirectResponse(f"/login?next={nxt}" if nxt != "/" else "/login", status_code=303)
    if staff and sess["role"] != "STAFF":
        return error_page(403, "This page is for staff only.")
    return _file(name)


@router.get("/login")
def login_page(request: Request):
    return RedirectResponse("/", 303) if auth.session(request) else _file("login.html")


@router.get("/")
def index(request: Request):
    sess = auth.session(request)
    return _gate(request, "overview.html" if sess and sess["role"] == "STAFF" else "home.html")


@router.get("/shipments")
def shipments(request: Request):
    return _gate(request, "shipments.html")


@router.get("/shipments/new")
def shipments_new(request: Request):
    return _gate(request, "book.html")


@router.get("/shipments/{shipment_id:int}")
def shipment_detail(request: Request, shipment_id: int):
    gate = _gate(request, "shipment.html")
    if not isinstance(gate, FileResponse):
        return gate
    sess = auth.session(request)
    try:
        require_shipment_access(sess, shipment_id)
    except AppError as exc:
        return error_page(exc.status_code, exc.message)
    return gate


@router.get("/network")
def network(request: Request):
    return _gate(request, "network.html", staff=True)


@router.get("/customers")
def customers(request: Request):
    return _gate(request, "customers.html", staff=True)


@router.get("/customers/{customer_id:int}")
def customer_detail(request: Request, customer_id: int):
    return _gate(request, "customer.html", staff=True)


@router.get("/reports")
@router.get("/reports/{report_id}")
def reports(request: Request, report_id: str = ""):
    return _gate(request, "reports.html", staff=True)


@router.get("/account")
def account(request: Request):
    return _gate(request, "account.html")


# ---- old .html URLs: 301 to the new ones
LEGACY = {
    "/login.html": "/login", "/index.html": "/", "/home.html": "/", "/dashboard.html": "/",
    "/parcels.html": "/shipments", "/book.html": "/shipments/new", "/route.html": "/network",
    "/hub.html": "/network?tab=impact", "/reports.html": "/reports", "/customers.html": "/customers",
    "/profile.html": "/account",
}
SHIPMENT_LEGACY = ("/track.html", "/live.html", "/delivered.html")


def _legacy(target: str):
    def go():
        return RedirectResponse(target, status_code=301)
    return go


for old, new in LEGACY.items():
    router.add_api_route(old, _legacy(new), methods=["GET"])


def _legacy_shipment(request: Request):
    sid = request.query_params.get("id", "")
    return RedirectResponse(f"/shipments/{sid}" if sid.isdigit() else "/shipments", status_code=301)


for old in SHIPMENT_LEGACY:
    router.add_api_route(old, _legacy_shipment, methods=["GET"])
