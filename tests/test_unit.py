"""No database needed: runs in CI without secrets."""
import pytest
from fastapi.testclient import TestClient

from backend import ratelimit
from backend.errors import TooManyRequests
from backend.main import app
from backend.schemas import PackageIn, ShipmentCreate
from backend.services.status import next_statuses

client = TestClient(app)


@pytest.mark.parametrize("history,expected", [
    ([], ["BOOKED"]),
    (["BOOKED"], ["PICKED_UP", "CANCELLED", "DELAYED"]),
    (["BOOKED", "PICKED_UP"], ["IN_TRANSIT", "DELAYED"]),
    (["BOOKED", "PICKED_UP", "IN_TRANSIT"], ["AT_BRANCH", "OUT_FOR_DELIVERY", "DELAYED"]),
    (["IN_TRANSIT", "AT_BRANCH"], ["IN_TRANSIT", "OUT_FOR_DELIVERY", "DELAYED"]),
    (["IN_TRANSIT", "OUT_FOR_DELIVERY"], ["DELIVERED", "DELAYED"]),
    (["OUT_FOR_DELIVERY", "DELIVERED"], []),
    (["BOOKED", "CANCELLED"], []),
    (["BOOKED", "DELAYED"], ["PICKED_UP", "CANCELLED"]),                  # delayed before pickup
    (["BOOKED", "PICKED_UP", "IN_TRANSIT", "DELAYED"], ["IN_TRANSIT", "AT_BRANCH", "OUT_FOR_DELIVERY"]),
])
def test_status_order(history, expected):
    assert next_statuses(history) == expected


def test_cancelled_only_before_pickup():
    assert "CANCELLED" in next_statuses(["BOOKED"])
    for h in (["BOOKED", "PICKED_UP"], ["BOOKED", "PICKED_UP", "IN_TRANSIT"], ["OUT_FOR_DELIVERY"]):
        assert "CANCELLED" not in next_statuses(h)


def test_rate_limiter():
    ratelimit.reset()
    for _ in range(3):
        ratelimit.check("k", 3)
    with pytest.raises(TooManyRequests):
        ratelimit.check("k", 3)


def test_package_validation():
    with pytest.raises(Exception):
        PackageIn(description="x", dimensions="1x1x1", packageType="Box", weightKg=0)
    with pytest.raises(Exception):
        ShipmentCreate(receiver=2, branchId=1, shipmentType="TELEPORT", packages=[])


def test_health_and_headers():
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "permissions-policy" in r.headers


def test_legacy_redirects():
    for old, new in [("/login.html", "/login"), ("/dashboard.html", "/"), ("/parcels.html", "/shipments"),
                     ("/book.html", "/shipments/new"), ("/route.html", "/network"),
                     ("/track.html?id=7", "/shipments/7"), ("/reports.html", "/reports")]:
        r = client.get(old, follow_redirects=False)
        assert r.status_code == 301 and r.headers["location"] == new, old


def test_anonymous_pages_and_errors():
    r = TestClient(app).get("/shipments", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login")
    r = TestClient(app).get("/no/such/page")
    assert r.status_code == 404 and "text/html" in r.headers["content-type"] and "{" not in r.text[:5]
    r = TestClient(app).get("/api/nope")
    assert r.status_code == 404 and r.json()["code"] == "NOT_FOUND"
    r = TestClient(app).get("/api/shipments")
    assert r.status_code == 401 and r.json()["code"] == "UNAUTHENTICATED"


def test_csrf_blocks_foreign_origin():
    r = TestClient(app).post("/api/auth/logout", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403 and r.json()["code"] == "CSRF"
