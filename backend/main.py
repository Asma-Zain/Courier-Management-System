"""Courier Tracking System - FastAPI app (Neo4j). Run: uvicorn backend.main:app --reload"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from neo4j.exceptions import ConstraintError, Neo4jError, ServiceUnavailable
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, db
from .errors import AppError
from .routers import auth, customers, graph, reports, routes, shipments, tracking

log = logging.getLogger("courier")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.require_config()
    yield
    db.close_driver()


TAGS = [
    {"name": "Auth", "description": "Demo email-only login with a signed HttpOnly session cookie."},
    {"name": "Customers", "description": "Customer CRUD. Staff manage all; a customer sees only their own profile."},
    {"name": "Shipments", "description": "Book (several packages in one transaction), list and view shipments."},
    {"name": "Tracking", "description": "Journey timeline, append events, current status board."},
    {"name": "Payments", "description": "One payment per shipment, amount at most the shipment total."},
    {"name": "Routes", "description": "Fewest hops / fewest km between hubs, hub impact."},
    {"name": "Reports", "description": "Dashboard and graph query reports G7-G16."},
    {"name": "Graph", "description": "JSON nodes/edges for visualisation."},
]

app = FastAPI(
    title="Courier Tracking System (Neo4j)",
    description="REST API over the Courier graph database. Log in via **POST /api/auth/login** "
                "(e.g. `divya@courier.com` staff, `arun@example.com` customer), then call the other endpoints.",
    version="1.0.0",
    openapi_tags=TAGS,
    lifespan=lifespan,
)

if config.CORS_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(AppError)
async def app_error(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(ConstraintError)
async def constraint_error(request: Request, exc: ConstraintError):
    return JSONResponse(status_code=409, content={
        "detail": "A record with that id or email already exists (or a concurrent change collided). "
                  "Nothing was saved."})


@app.exception_handler(ServiceUnavailable)
async def unavailable(request: Request, exc: ServiceUnavailable):
    log.error("Database unavailable: %s", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "The database is temporarily unavailable."})


@app.exception_handler(Neo4jError)
async def neo4j_error(request: Request, exc: Neo4jError):
    log.error("Neo4j error: %s", getattr(exc, "code", type(exc).__name__))
    return JSONResponse(status_code=500, content={"detail": "Database error."})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    problems = [f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "; ".join(problems) or "Invalid request."})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.error("Unhandled error: %s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong."})


for r in (auth, customers, shipments, tracking, routes, reports, graph):
    app.include_router(r.router)

# Static frontend last, so /api and /docs win.
app.mount("/", StaticFiles(directory=config.STATIC_DIR, html=True), name="static")
