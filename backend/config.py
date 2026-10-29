"""Environment configuration. Values are read once; nothing here is ever logged."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "app" / ".env")
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PROD = APP_ENV == "production"

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

APP_SECRET = os.getenv("APP_SECRET", "")
COOKIE_SECURE = IS_PROD or _bool("COOKIE_SECURE", False)
ENABLE_DOCS = _bool("ENABLE_DOCS", not IS_PROD)
# Clickable demo logins on the login page. On by default in development, off in production unless enabled.
SHOW_DEMO_LOGINS = _bool("SHOW_DEMO_LOGINS", not IS_PROD)
ALLOWED_ORIGINS = [o.strip().rstrip("/") for o in
                   (os.getenv("ALLOWED_ORIGINS") or os.getenv("CORS_ORIGINS", "")).split(",") if o.strip()]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
SESSION_HOURS = 8

STATIC_DIR = ROOT / "static"
PAGES_DIR = STATIC_DIR / "pages"

# Fixed whitelists
VALID_STATUSES = ["BOOKED", "PICKED_UP", "IN_TRANSIT", "AT_BRANCH",
                  "OUT_FOR_DELIVERY", "DELIVERED", "DELAYED", "CANCELLED"]
SHIPMENT_TYPES = ["STANDARD", "EXPRESS", "OVERNIGHT"]
PACKAGE_TYPES = ["Envelope", "Box", "Parcel"]
PAYMENT_MODES = ["UPI", "CARD", "NETBANKING", "CASH"]
PAYMENT_STATUSES = ["PAID", "PENDING"]

# Demo rate card used when a booking does not give an amount: base rupees + rupees per kg
RATE_CARD = {"STANDARD": (100.0, 20.0), "EXPRESS": (120.0, 40.0), "OVERNIGHT": (150.0, 60.0)}


def require_config() -> None:
    missing = [n for n, v in (("NEO4J_URI", NEO4J_URI), ("NEO4J_PASSWORD", NEO4J_PASSWORD),
                              ("APP_SECRET", APP_SECRET)) if not v]
    if missing:
        raise RuntimeError("Missing environment variables: " + ", ".join(missing))
    if IS_PROD and len(APP_SECRET) < 32:
        raise RuntimeError("APP_SECRET must be at least 32 characters in production.")
