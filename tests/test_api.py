import pytest
from fastapi.testclient import TestClient

from backend.main import app
from tests.conftest import BASELINE, cleanup, counts, make_client

pytestmark = pytest.mark.usefixtures("dbclean")


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
    ids = {s["shipmentId"] for s in arun.get("/api/shipments").json()["items"]}
    assert ids == {1, 4, 10000}


def test_customer_blocked_from_staff_endpoints(arun):
    for path in ("/api/customers", "/api/overview", "/api/shipments/status",
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
    rows = {r["branch"]: (r["shipments"], r["value"]) for r in staff.get("/api/reports/branch-performance").json()["rows"]}
    assert rows["Chennai Central Branch"] == (3, 490.0)
    assert rows["Bengaluru City Branch"] == (2, 440.0)


def test_other_reports_run(staff):
    cleanup()
    for name in ("busiest-locations", "delayed", "employee-activity", "payments", "packages-per-shipment",
                 "heavier-than-average", "customer-activity", "tracking-duration"):
        r = staff.get(f"/api/reports/{name}")
        assert r.status_code == 200 and r.json()["rows"], name
        assert r.json()["report"]["cypher"] and r.json()["report"]["id"].startswith("G")
    assert staff.get("/api/reports/delayed").json()["rows"][0]["shipment"] == 4
    cat = staff.get("/api/reports").json()
    assert {r["id"] for r in cat} == {f"G{n}" for n in (7, 8, 9, 10, 11, 12, 13, 14, 15, 16)}
    assert staff.get("/api/reports/nope").status_code == 404
    assert staff.get("/api/reports/customer-network").status_code == 200
    o = staff.get("/api/overview").json()
    assert o["system"]["counts"] == BASELINE
    assert o["kpis"]["active"] == 5 and o["kpis"]["delayed"] == 1 and o["kpis"]["outForDelivery"] == 1


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


def _two_customers(staff, city="Chennai"):
    cleanup()
    for cid in (9001, 9002):
        body = customer_body(cid, f"t{cid}@example.com")
        body["city"] = city
        assert staff.post("/api/customers", json=body).status_code == 201


def _event(staff, sid, status, branch="Chennai Hub", **extra):
    return staff.post(f"/api/shipments/{sid}/events", json={"status": status, "branch": branch, **extra})


def test_book_two_packages_track_event_payment(staff):
    _two_customers(staff, city="Chennai")
    book = {"sender": 9001, "receiverEmail": "T9002@example.com", "branchId": 1, "shipmentType": "STANDARD",
            "packages": [{"description": "Gift box", "dimensions": "30x30x15 cm", "packageType": "Box", "weightKg": 2.0},
                         {"description": "Cards", "dimensions": "25x15x5 cm", "packageType": "Envelope", "weightKg": 1.5}]}
    r = staff.post("/api/shipments", json=book)
    assert r.status_code == 201, r.text
    sid = r.json()["shipmentId"]
    assert r.json()["weightKg"] == 3.5 and r.json()["packages"] == 2 and r.json()["totalAmount"] == 170.0
    detail = staff.get(f"/api/shipments/{sid}").json()
    assert len(detail["packages"]) == 2 and detail["status"] == "BOOKED" and detail["payment"] is None
    assert detail["paymentState"] == "UNPAID" and detail["outstanding"] == 170.0
    assert detail["sender"]["customerId"] == 9001 and detail["bookedAt"] == "Chennai Central Branch"
    assert detail["since"].endswith("Z")                       # API timestamps are UTC

    # customer cannot see it (Arun is neither sender nor receiver)
    assert make_client("arun@example.com").get(f"/api/shipments/{sid}").status_code == 403

    # status order is enforced and exposed
    assert staff.get(f"/api/shipments/{sid}/next-statuses").json()["allowed"] == ["PICKED_UP", "CANCELLED", "DELAYED"]
    bad = _event(staff, sid, "DELIVERED")
    assert bad.status_code == 409 and bad.json()["code"] == "INVALID_TRANSITION"
    assert bad.json()["allowed"] == ["PICKED_UP", "CANCELLED", "DELAYED"]
    assert _event(staff, sid, "FLYING").status_code == 422
    assert _event(staff, sid, "PICKED_UP", "Atlantis").status_code == 404
    assert _event(staff, 424242, "PICKED_UP").status_code == 404
    ev = _event(staff, sid, "picked_up", "Chennai Central Branch", note="Collected at the counter")
    assert ev.status_code == 201 and ev.json()["step"] == 2
    assert _event(staff, sid, "IN_TRANSIT").status_code == 201
    assert _event(staff, sid, "DELAYED").status_code == 201
    nxt = staff.get(f"/api/shipments/{sid}/next-statuses").json()
    assert nxt["allowed"] == ["IN_TRANSIT", "AT_BRANCH", "OUT_FOR_DELIVERY"] and nxt["currentPlace"] == "Chennai Hub"
    assert _event(staff, sid, "OUT_FOR_DELIVERY").status_code == 201
    journey = staff.get(f"/api/shipments/{sid}/track").json()
    assert [j["status"] for j in journey] == ["BOOKED", "PICKED_UP", "IN_TRANSIT", "DELAYED", "OUT_FOR_DELIVERY"]
    assert journey[1]["note"] == "Collected at the counter" and journey[1]["loggedBy"] == "Divya"
    g = staff.get(f"/api/graph/shipment/{sid}").json()
    assert sum(1 for e in g["edges"] if e["label"] == "NEXT") == 4

    # delivery only in the receiver's city (Chennai)
    wrong = _event(staff, sid, "DELIVERED", "Bengaluru City Branch")
    assert wrong.status_code == 409 and wrong.json()["code"] == "WRONG_DELIVERY_LOCATION"
    assert _event(staff, sid, "DELIVERED", "Chennai Hub").status_code == 201
    assert _event(staff, sid, "AT_BRANCH").status_code == 409
    assert staff.get(f"/api/shipments/{sid}/next-statuses").json()["allowed"] == []

    # payments
    assert staff.post(f"/api/shipments/{sid}/payment", json={"amount": 171, "mode": "UPI"}).status_code == 400
    assert staff.post(f"/api/shipments/{sid}/payment", json={"amount": -5, "mode": "UPI"}).status_code == 422
    ok = staff.post(f"/api/shipments/{sid}/payment", json={"amount": 100, "mode": "UPI", "status": "PAID"})
    assert ok.status_code == 201, ok.text
    assert staff.post(f"/api/shipments/{sid}/payment", json={"amount": 70, "mode": "UPI"}).status_code == 409
    assert staff.get(f"/api/shipments/{sid}").json()["paymentState"] == "PARTIAL"

    # customers with shipments cannot be deleted
    assert staff.delete("/api/customers/9001").status_code == 409


def test_cancel_only_before_pickup_and_delivery_anywhere_without_branch_in_city(staff):
    _two_customers(staff, city="Madurai")              # no branch in Madurai: delivery place not restricted
    book = {"sender": 9001, "receiver": 9002, "branchId": 1, "shipmentType": "EXPRESS",
            "payment": {"mode": "UPI", "status": "PAID"},
            "packages": [{"description": "x", "dimensions": "10x10x10 cm", "packageType": "Box", "weightKg": 1}]}
    sid = staff.post("/api/shipments", json=book).json()["shipmentId"]
    assert staff.get(f"/api/shipments/{sid}").json()["paymentState"] == "PAID"      # paid at booking
    assert _event(staff, sid, "CANCELLED", "Chennai Central Branch").status_code == 201
    assert _event(staff, sid, "PICKED_UP", "Chennai Central Branch").status_code == 409
    sid2 = staff.post("/api/shipments", json={**book, "payment": None}).json()["shipmentId"]
    assert _event(staff, sid2, "PICKED_UP", "Chennai Central Branch").status_code == 201
    assert _event(staff, sid2, "CANCELLED", "Chennai Central Branch").status_code == 409
    for st, br in [("IN_TRANSIT", "Chennai Hub"), ("OUT_FOR_DELIVERY", "Chennai Hub"), ("DELIVERED", "Mumbai Hub")]:
        assert _event(staff, sid2, st, br).status_code == 201


def test_shipments_list_filters_search_pagination(staff, arun):
    cleanup()
    r = staff.get("/api/shipments").json()
    assert r["total"] == 5 and r["counts"]["ALL"] == 5 and r["counts"]["IN_TRANSIT"] == 3
    assert r["counts"]["ACTIVE"] == 5 and r["counts"]["DELAYED"] == 1
    assert [i["shipmentId"] for i in r["items"]][:1] == [10000]                     # newest first
    item = r["items"][0]
    assert item["sender"] == "Arun Kumar" and item["paymentState"] == "PAID" and item["place"] == "Chennai Hub"
    assert [i["shipmentId"] for i in staff.get("/api/shipments", params={"status": "DELAYED"}).json()["items"]] == [4]
    assert staff.get("/api/shipments", params={"q": "priya"}).json()["total"] == 2
    assert [i["shipmentId"] for i in staff.get("/api/shipments", params={"q": "10000"}).json()["items"]] == [10000]
    p1 = staff.get("/api/shipments", params={"pageSize": 2, "page": 1}).json()
    p3 = staff.get("/api/shipments", params={"pageSize": 2, "page": 3}).json()
    assert len(p1["items"]) == 2 and len(p3["items"]) == 1 and p1["total"] == 5
    amounts = [i["totalAmount"] for i in staff.get("/api/shipments", params={"sort": "amount"}).json()["items"]]
    assert amounts == sorted(amounts, reverse=True)
    assert staff.get("/api/shipments", params={"payment": "UNPAID"}).json()["total"] == 0
    assert staff.get("/api/shipments", params={"customerId": 1}).json()["total"] == 3
    assert staff.get("/api/shipments", params={"sort": "bogus"}).status_code == 422
    # customers: scoped by the server, cannot widen the scope
    mine = arun.get("/api/shipments", params={"q": "priya"}).json()
    assert {i["shipmentId"] for i in mine["items"]} == {1}
    assert arun.get("/api/shipments", params={"customerId": 2}).status_code == 403


def test_book_validation(staff):
    base = {"sender": 1, "receiver": 2, "branchId": 1, "shipmentType": "STANDARD",
            "packages": [{"description": "x", "dimensions": "1x1x1", "packageType": "Box", "weightKg": 1}]}
    assert staff.post("/api/shipments", json={**base, "packages": []}).status_code == 422
    assert staff.post("/api/shipments", json={**base, "shipmentType": "TELEPORT"}).status_code == 422
    bad = {**base, "packages": [{**base["packages"][0], "weightKg": 0}]}
    assert staff.post("/api/shipments", json=bad).status_code == 422
    assert staff.post("/api/shipments", json={**base, "receiver": 424242}).status_code == 404
    assert staff.post("/api/shipments", json={**base, "sender": None}).status_code == 400
    r = staff.post("/api/shipments", json={**base, "receiver": None, "receiverEmail": "nobody@x.com"})
    assert r.status_code == 404 and r.json()["code"] == "RECEIVER_NOT_FOUND"
    assert staff.post("/api/shipments", json={**base, "receiverEmail": "priya@example.com"}).status_code == 400  # both given


def test_customer_books_as_self(staff, arun):
    cleanup()
    assert staff.post("/api/customers", json=customer_body(9002, "t9002@example.com")).status_code == 201
    body = {"receiverEmail": "t9002@example.com", "branchId": 1, "shipmentType": "EXPRESS",
            "packages": [{"description": "Book", "dimensions": "20x15x4 cm", "packageType": "Parcel", "weightKg": 0.8}]}
    assert arun.post("/api/shipments", json={**body, "sender": 2}).status_code == 403
    r = arun.post("/api/shipments", json=body)
    assert r.status_code == 201
    assert staff.get(f"/api/shipments/{r.json()['shipmentId']}").json()["sender"]["customerId"] == 1
    cleanup()


def test_zz_baseline_restored():
    cleanup()
    assert counts() == BASELINE


def test_customer_lookup_privacy(arun, staff):
    r = arun.get("/api/customers/lookup", params={"email": "Priya@example.com"})
    assert r.status_code == 200 and r.json() == {"exists": True, "displayName": "Priya S."}
    assert arun.get("/api/customers/lookup", params={"email": "x@y.com"}).json() == {"exists": False}
    s = staff.get("/api/customers/lookup", params={"email": "priya@example.com"}).json()
    assert s["customerId"] == 2 and s["name"] == "Priya Sharma" and s["city"] == "Bengaluru"


def test_lookup_rate_limited(arun):
    codes = [arun.get("/api/customers/lookup", params={"email": "a@b.co"}).status_code for _ in range(32)]
    assert codes[:30] == [200] * 30 and codes[30:] == [429, 429]


def test_login_rate_limited():
    c = TestClient(app)
    codes = [c.post("/api/auth/login", json={"email": "nobody@nowhere.com"}).status_code for _ in range(12)]
    assert codes[:10] == [401] * 10 and codes[10:] == [429, 429]


def test_readyz_and_account_info(staff, arun):
    assert TestClient(app).get("/readyz").json() == {"status": "ready"}
    me = staff.get("/api/auth/me").json()
    assert me["branch"] == "Chennai Central Branch" and me["jobRole"] == "Tracking Executive"
    assert arun.get("/api/auth/me").json()["role"] == "CUSTOMER"


def test_pages_server_side_access(staff, arun):
    assert staff.get("/").status_code == 200 and "Overview" in staff.get("/").text
    assert staff.get("/shipments/2").status_code == 200
    assert staff.get("/shipments/424242").status_code == 404
    assert arun.get("/shipments/2").status_code == 403 and "text/html" in arun.get("/shipments/2").headers["content-type"]
    assert arun.get("/shipments/1").status_code == 200
    for path in ("/customers", "/customers/1", "/network", "/reports", "/reports/delayed"):
        r = arun.get(path)
        assert r.status_code == 403 and "staff only" in r.text.lower(), path
        assert staff.get(path).status_code == 200, path
    assert arun.get("/account").status_code == 200


def test_zz_baseline_restored():
    cleanup()
    assert counts() == BASELINE
