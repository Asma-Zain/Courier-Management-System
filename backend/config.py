"""Environment configuration. Values are read once; nothing here is ever logged."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "app" / ".env")
load_dotenv(ROOT / ".env")

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

APP_SECRET = os.getenv("APP_SECRET", "")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
SESSION_HOURS = 8

STATIC_DIR = ROOT / "static"

# Fixed whitelists (VALID_STATUSES is reused from the CLI)
VALID_STATUSES = [
    "BOOKED", "PICKED_UP", "IN_TRANSIT", "AT_BRANCH",
    "OUT_FOR_DELIVERY", "DELIVERED", "DELAYED", "CANCELLED",
]
TERMINAL_STATUSES = {"DELIVERED", "CANCELLED"}
SHIPMENT_TYPES = ["STANDARD", "EXPRESS", "OVERNIGHT"]
PACKAGE_TYPES = ["Envelope", "Box", "Parcel"]
PAYMENT_MODES = ["UPI", "CARD", "NETBANKING", "CASH"]
PAYMENT_STATUSES = ["PAID", "PENDING"]

# Demo rate card used when a booking does not give an amount: base + per-kg
RATE_CARD = {"STANDARD": (100.0, 20.0), "EXPRESS": (120.0, 40.0), "OVERNIGHT": (150.0, 60.0)}


def require_config() -> None:
    missing = [n for n, v in (("NEO4J_URI", NEO4J_URI), ("NEO4J_PASSWORD", NEO4J_PASSWORD),
                              ("APP_SECRET", APP_SECRET)) if not v]
    if missing:
        raise RuntimeError("Missing environment variables: " + ", ".join(missing))
