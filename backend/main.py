"""Parcelly - FastAPI app (Neo4j). Run: uvicorn backend.main:app --reload"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from neo4j.exceptions import ConstraintError, Neo4jError, ServiceUnavailable
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.gzip import GZipMiddleware

from . import config, db, pages
from .errors import AppError
from .routers import auth, customers, graph, reports, routes, shipments, tracking
from .security import SecurityMiddleware

logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("courier")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.require_config()
    yield
    db.close_driver()


TAGS = [
    {"name": "Auth", "description": "Demo email-only login with a signed HttpOnly session cookie."},
    {"name": "Customers", "description": "Customer CRUD. Staff manage all; a customer sees only their own profile."},
    {"name": "Shipments", "description": "Book (several packages in one transaction), list, search and view shipments."},
    {"name": "Tracking", "description": "Journey timeline, append events (status order enforced), current status board."},
    {"name": "Payments", "description": "One payment per shipment, amount at most the outstanding balance."},
    {"name": "Routes", "description": "Fewest hops / fewest km between hubs, hub impact."},
    {"name": "Reports", "description": "Overview, report catalogue and reports G7-G16."},
    {"name": "Graph", "description": "JSON nodes/edges for visualisation."},
    {"name": "Health", "description": "Liveness and readiness probes."},
]

app = FastAPI(
    title="Parcelly API (Neo4j)",
    description="REST API over the Courier graph database. Log in via **POST /api/auth/login** "
                "(e.g. `divya@courier.com` staff, `arun@example.com` customer), then call the other endpoints.",
    version="2.0.0",
    openapi_tags=TAGS,
    lifespan=lifespan,
    docs_url="/docs" if config.ENABLE_DOCS else None,
    redoc_url="/redoc" if config.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if config.ENABLE_DOCS else None,
)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(SecurityMiddleware)
if config.ALLOWED_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=config.ALLOWED_ORIGINS, allow_credentials=True,
                       allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type"])


def _wants_html(request: Request) -> bool:
    return not request.url.path.startswith("/api")


def _json(status: int, detail: str, code: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail, "code": code, **extra})


@app.exception_handler(AppError)
async def app_error(request: Request, exc: AppError):
    if _wants_html(request):
        return pages.error_page(exc.status_code, exc.message)
    return _json(exc.status_code, exc.message, exc.code, **exc.extra)


@app.exception_handler(ConstraintError)
async def constraint_error(request: Request, exc: ConstraintError):
    return _json(409, "A record with that id or email already exists (or a concurrent change collided). "
                      "Nothing was saved.", "CONFLICT")


@app.exception_handler(ServiceUnavailable)
async def unavailable(request: Request, exc: ServiceUnavailable):
    log.error("Database unavailable: %s", type(exc).__name__)
    return _json(503, "The database is temporarily unavailable.", "DB_UNAVAILABLE")


@app.exception_handler(Neo4jError)
async def neo4j_error(request: Request, exc: Neo4jError):
    log.error("Neo4j error: %s", getattr(exc, "code", type(exc).__name__))
    return _json(500, "Database error.", "DB_ERROR")


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    if _wants_html(request) and exc.status_code in (403, 404):
        return pages.error_page(exc.status_code)
    codes = {401: "UNAUTHENTICATED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
    return _json(exc.status_code, str(exc.detail), codes.get(exc.status_code, f"HTTP_{exc.status_code}"))


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    fields = {}
    for e in exc.errors():
        fields[".".join(str(p) for p in e["loc"][1:])] = e["msg"]
    detail = "; ".join(f"{k}: {v}" if k else v for k, v in fields.items()) or "Invalid request."
    return _json(422, detail, "VALIDATION", fields=fields)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.error("Unhandled error: %s", type(exc).__name__)
    if _wants_html(request):
        return pages.error_page(500)
    return _json(500, "Something went wrong.", "INTERNAL")


@app.get("/healthz", tags=["Health"], summary="Process is alive")
def healthz():
    return {"status": "ok"}


@app.get("/readyz", tags=["Health"], summary="Neo4j connection works")
def readyz():
    try:
        db.read("RETURN 1 AS ok")
    except Exception as exc:
        log.error("Not ready: %s", type(exc).__name__)
        return _json(503, "Database not reachable.", "NOT_READY")
    return {"status": "ready"}


for r in (auth, customers, shipments, tracking, routes, reports, graph):
    app.include_router(r.router)
app.include_router(pages.router)

for folder in ("css", "js", "img", "vendor"):
    (config.STATIC_DIR / folder).mkdir(exist_ok=True)
    app.mount(f"/{folder}", StaticFiles(directory=config.STATIC_DIR / folder), name=folder)
