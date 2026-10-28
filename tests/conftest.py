"""Tests run against the real Aura database but only touch test ids (customers 9001/9002 and
whatever they send). A cleanup runs before and after the session, then baseline counts are checked."""
import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.main import app

BASELINE = {"Branch": 6, "Customer": 4, "Employee": 3, "Package": 7, "Payment": 5,
            "Shipment": 5, "TrackingEvent": 12}
TEST_CUSTOMERS = [9001, 9002]


def counts() -> dict:
    return {r["label"]: r["n"] for r in db.read("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n")}


def cleanup() -> None:
    def work(tx):
        db.run(tx, """
            MATCH (c:Customer) WHERE c.customerId IN $ids
            OPTIONAL MATCH (s:Shipment) WHERE EXISTS { (c)-[:SENT]->(s) } OR EXISTS { (s)-[:ADDRESSED_TO]->(c) }
            OPTIONAL MATCH (s)-[:CONTAINS]->(p:Package)
            OPTIONAL MATCH (s)-[:HAS_EVENT]->(t:TrackingEvent)
            OPTIONAL MATCH (pay:Payment)-[:PAYS_FOR]->(s)
            DETACH DELETE p, t, pay, s
        """, {"ids": TEST_CUSTOMERS})
        db.run(tx, "MATCH (c:Customer) WHERE c.customerId IN $ids DETACH DELETE c", {"ids": TEST_CUSTOMERS})
    db.write(work)


@pytest.fixture(scope="session", autouse=True)
def _session_cleanup():
    with TestClient(app):
        cleanup()
        yield
        cleanup()
        assert counts() == BASELINE, "baseline counts were not restored"


def make_client(email: str) -> TestClient:
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"email": email})
    assert r.status_code == 200, r.text
    return c


@pytest.fixture()
def staff():
    return make_client("divya@courier.com")


@pytest.fixture()
def arun():
    return make_client("arun@example.com")
