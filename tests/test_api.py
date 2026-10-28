import pytest
from fastapi.testclient import TestClient

from backend.main import app
from tests.conftest import BASELINE, cleanup, counts, make_client


def customer_body(cid, email):
    return {"customerId": cid, "firstName": "Test", "lastName": f"User{cid}", "email": email,
            "phone": "9000000099", "street": "1 Test Street", "city": "Chennai",
            "state": "Tamil Nadu", "pincode": "600001"}


# ---------------------------------------------------------------- auth
def test_login_roles():
    assert make_client("divya@courier.com").get("/api/auth/me").json()["role"] == "STAFF"
    assert make_client("naveen@courier.com").get("/api/auth/me").json()["role"] == "STAFF"
    me = make_client("arun@example.com").get("/api/auth/me").json()
    assert me["role"] == "CUSTOMER" and me["id"] == 1


def test_login_unknown_and_logout():
    c = TestClient(app)
    assert c.post("/api/auth/login", json={"email": "nobody@nowhere.com"}).status_code == 401
    assert c.get("/api/auth/me").status_code == 401
    c = make_client("priya@example.com")
    assert c.post("/api/auth/logout").status_code == 200
    assert c.get("/api/auth/me").status_code == 401


def test_tampered_cookie_rejected():
    c = TestClient(app)
    c.cookies.set("courier_session", "garbage")
    assert c.get("/api/auth/me").status_code == 401


# ---------------------------------------------------------- access control
def test_customer_denied_on_others_shipment(arun):
    assert arun.get("/api/shipments/2").status_code == 403
    assert arun.get("/api/shipments/2/track").status_code == 403
    assert arun.get("/api/graph/shipment/2").status_code == 403
    assert arun.get("/api/shipments/1").status_code == 200
    assert arun.get("/api/shipments/4/track").status_code == 200  # received


def test_customer_sees_only_own_shipments(arun):
    ids = {s["shipmentId"] for s in arun.get("/api/shipments").json()}
    assert ids == {1, 4, 10000}


def test_customer_blocked_from_staff_endpoints(arun):
    for path in ("/api/customers", "/api/dashboard", "/api/shipments/status",
                 "/api/reports/branch-performance", "/api/hubs/Chennai Hub/impact", "/api/customers/2"):
        assert arun.get(path).status_code == 403, path
    assert arun.get("/api/customers/1").status_code == 200
    r = arun.post("/api/shipments/1/events", json={"status": "DELAYED", "branch": "Chennai Hub"})
    assert r.status_code == 403


def test_unknown_shipment_404(staff):
    assert staff.get("/api/shipments/424242").status_code == 404


# ------------------------------------------------------ known baseline values
def test_status_board_g3(staff):
    board = {r["shipment"]: (r["status"], r["place"]) for r in staff.get("/api/shipments/status").json()}
    assert board == {1: ("IN_TRANSIT", "Chennai Hub"), 2: ("OUT_FOR_DELIVERY", "Bengaluru City Branch"),
                     3: ("IN_TRANSIT", "Hyderabad Hub"), 4: ("DELAYED", "Chennai Hub"),
                     10000: ("IN_TRANSIT", "Chennai Hub")}


def test_routes_g4_g5(staff):
    p = {"from": "Hyderabad Hub", "to": "Coimbatore Hub"}
    assert staff.get("/api/routes/fewest-hops", params=p).json()["hops"] == 2
    top = staff.get("/api/routes/fewest-km", params=p).json()
    assert [r["km"] for r in top] == [935, 1130, 1345]
    assert top[0]["route"] == ["Hyderabad Hub", "Bengaluru City Branch", "Coimbatore Hub"]


def test_route_errors(staff):
    assert staff.get("/api/routes/fewest-km", params={"from": "Nowhere", "to": "Chennai Hub"}).status_code == 404
    assert staff.get("/api/routes/fewest-km", params={"from": "Chennai Hub", "to": "Chennai Hub"}).status_code == 400


def test_branch_performance_g10(staff):
    rows = {r["branch"]: (r["shipments"], r["value"]) for r in staff.get("/api/reports/branch-performance").json()}
    assert rows["Chennai Central Branch"] == (3, 490.0)
    assert rows["Bengaluru City Branch"] == (2, 440.0)


def test_other_reports_run(staff):
    for name in ("busiest-locations", "delayed", "employee-activity", "payments", "packages-per-shipment",
                 "heavier-than-average", "customer-activity", "tracking-duration"):
        r = staff.get(f"/api/reports/{name}")
        assert r.status_code == 200 and r.json(), name
    assert staff.get("/api/reports/delayed").json()[0]["shipment"] == 4
    assert staff.get("/api/reports/customer-network").status_code == 200
    d = staff.get("/api/dashboard").json()
    assert {c["label"]: c["nodes"] for c in d["counts"]} == BASELINE


def test_hub_impact_g6(staff):
    rows = staff.get("/api/hubs/Chennai Hub/impact").json()
    assert [r["shipment"] for r in rows] == [1, 4, 10000]
    assert staff.get("/api/hubs/Nope/impact").status_code == 404


def test_graph_json(staff):
    g = staff.get("/api/graph/shipment/10000").json()
    assert {e["label"] for e in g["edges"]} == {"HAS_EVENT", "AT", "NEXT"}
    assert len(g["nodes"]) == 1 + 2 + 2
    n = staff.get("/api/graph/network").json()
    assert len(n["nodes"]) == 6 and len(n["edges"]) == 8 and "km" in n["edges"][0]


# --------------------------------------------------- writes (test ids only)
def test_customer_crud_and_duplicate_409(staff):
    cleanup()
    assert staff.post("/api/customers", json=customer_body(9001, "t9001@example.com")).status_code == 201
    # duplicate key (C7)
    r = staff.post("/api/customers", json=customer_body(9001, "other9001@example.com"))
    assert r.status_code == 409 and "exists" in r.json()["detail"]
    # duplicate email
    assert staff.post("/api/customers", json=customer_body(9002, "t9001@example.com")).status_code == 409
    # validation
    bad = customer_body(9002, "t9002@example.com"); bad["phone"] = "123"
    assert staff.post("/api/customers", json=bad).status_code == 422
    # update + customer role cannot touch others
    r = staff.patch("/api/customers/9001", json={"phone": "9876500099", "city": "Madurai"})
    assert r.json()["phone"] == "9876500099" and r.json()["city"] == "Madurai"
    assert staff.patch("/api/customers/424242", json={"phone": "9876500099"}).status_code == 404
    assert staff.delete("/api/customers/9001").status_code == 204
    assert staff.get("/api/customers/9001").status_code == 404
    assert staff.delete("/api/customers/9001").status_code == 404


def test_book_two_packages_track_event_payment(staff):
    cleanup()
    for cid in (9001, 9002):
        assert staff.post("/api/customers", json=customer_body(cid, f"t{cid}@example.com")).status_code == 201
    book = {"sender": 9001, "receiver": 9002, "branchId": 1, "shipmentType": "STANDARD",
            "packages": [{"description": "Gift box", "dimensions": "30x30x15 cm", "packageType": "Box", "weightKg": 2.0},
                         {"description": "Cards", "dimensions": "25x15x5 cm", "packageType": "Envelope", "weightKg": 1.5}]}
    r = staff.post("/api/shipments", json=book)
    assert r.status_code == 201, r.text
    sid = r.json()["shipmentId"]
    assert r.json()["weightKg"] == 3.5 and r.json()["packages"] == 2
    detail = staff.get(f"/api/shipments/{sid}").json()
    assert len(detail["packages"]) == 2 and detail["status"] == "BOOKED" and detail["payment"] is None
    assert detail["sender"]["customerId"] == 9001 and detail["bookedAt"] == "Chennai Central Branch"

    # customer cannot see it (Arun is neither sender nor receiver)
    assert make_client("arun@example.com").get(f"/api/shipments/{sid}").status_code == 403

    # events
    ev = staff.post(f"/api/shipments/{sid}/events", json={"status": "in_transit", "branch": "Chennai Hub"})
    assert ev.status_code == 201 and ev.json()["step"] == 2 and ev.json()["status"] == "IN_TRANSIT"
    assert staff.post(f"/api/shipments/{sid}/events", json={"status": "FLYING", "branch": "Chennai Hub"}).status_code == 422
    assert staff.post(f"/api/shipments/{sid}/events", json={"status": "DELAYED", "branch": "Atlantis"}).status_code == 404
    assert staff.post("/api/shipments/424242/events", json={"status": "DELAYED", "branch": "Chennai Hub"}).status_code == 404
    journey = staff.get(f"/api/shipments/{sid}/track").json()
    assert [j["status"] for j in journey] == ["BOOKED", "IN_TRANSIT"]
    g = staff.get(f"/api/graph/shipment/{sid}").json()
    assert sum(1 for e in g["edges"] if e["label"] == "NEXT") == 1
    # current status follows the chain
    assert staff.get(f"/api/shipments/{sid}").json()["status"] == "IN_TRANSIT"
    assert staff.post(f"/api/shipments/{sid}/events", json={"status": "DELIVERED", "branch": "Chennai Hub"}).status_code == 201
    assert staff.post(f"/api/shipments/{sid}/events", json={"status": "AT_BRANCH", "branch": "Chennai Hub"}).status_code == 409

    # payments
    total = detail["totalAmount"]
    assert staff.post(f"/api/shipments/{sid}/payment", json={"amount": total + 1, "mode": "UPI"}).status_code == 400
    assert staff.post(f"/api/shipments/{sid}/payment", json={"amount": -5, "mode": "UPI"}).status_code == 422
    ok = staff.post(f"/api/shipments/{sid}/payment", json={"amount": total, "mode": "UPI", "status": "PAID"})
    assert ok.status_code == 201, ok.text
    assert staff.post(f"/api/shipments/{sid}/payment", json={"amount": total, "mode": "UPI"}).status_code == 409

    # customers with shipments cannot be deleted
    assert staff.delete("/api/customers/9001").status_code == 409


def test_book_validation(staff):
    base = {"sender": 1, "receiver": 2, "branchId": 1, "shipmentType": "STANDARD",
            "packages": [{"description": "x", "dimensions": "1x1x1", "packageType": "Box", "weightKg": 1}]}
    assert staff.post("/api/shipments", json={**base, "packages": []}).status_code == 422
    assert staff.post("/api/shipments", json={**base, "shipmentType": "TELEPORT"}).status_code == 422
    bad = {**base, "packages": [{**base["packages"][0], "weightKg": 0}]}
    assert staff.post("/api/shipments", json=bad).status_code == 422
    assert staff.post("/api/shipments", json={**base, "receiver": 424242}).status_code == 404
    assert staff.post("/api/shipments", json={**base, "sender": None}).status_code == 400


def test_customer_books_as_self(staff, arun):
    cleanup()
    assert staff.post("/api/customers", json=customer_body(9002, "t9002@example.com")).status_code == 201
    body = {"receiver": 9002, "branchId": 1, "shipmentType": "EXPRESS",
            "packages": [{"description": "Book", "dimensions": "20x15x4 cm", "packageType": "Parcel", "weightKg": 0.8}]}
    assert arun.post("/api/shipments", json={**body, "sender": 2}).status_code == 403
    r = arun.post("/api/shipments", json=body)
    assert r.status_code == 201
    assert staff.get(f"/api/shipments/{r.json()['shipmentId']}").json()["sender"]["customerId"] == 1
    cleanup()


def test_zz_baseline_restored():
    cleanup()
    assert counts() == BASELINE


def test_customer_lookup(arun):
    r = arun.get("/api/customers/lookup", params={"email": "Priya@example.com"})
    assert r.status_code == 200 and r.json() == {"customerId": 2, "name": "Priya Sharma", "city": "Bengaluru"}
    assert arun.get("/api/customers/lookup", params={"email": "x@y.com"}).status_code == 404
