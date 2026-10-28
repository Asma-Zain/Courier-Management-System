from .. import config, db
from ..errors import BadRequest, Conflict, NotFound
from .common import ACCESS, access_params, require_shipment_access

# current status = the TrackingEvent with no outgoing NEXT
CURRENT_STATUS = """
OPTIONAL MATCH (s)-[:HAS_EVENT]->(cur:TrackingEvent) WHERE NOT (cur)-[:NEXT]->()
OPTIONAL MATCH (cur)-[:AT]->(curBranch:Branch)
"""
STATUS_RANK = {"BOOKED": 0, "PICKED_UP": 1, "IN_TRANSIT": 2, "AT_BRANCH": 3, "OUT_FOR_DELIVERY": 4,
               "DELAYED": 5, "DELIVERED": 6, "CANCELLED": 7}
ACTIVE_EXCLUDE = {"DELIVERED", "CANCELLED"}


def payment_state(total: float, paid: float) -> str:
    if paid >= total and total > 0:
        return "PAID"
    return "PARTIAL" if paid > 0 else "UNPAID"


def list_shipments(user: dict, q: str | None = None, status: str | None = None, payment: str | None = None,
                   sort: str = "newest", page: int = 1, page_size: int = 20,
                   customer_id: int | None = None) -> dict:
    """Scoped by role in Cypher (ACCESS). Search runs in Cypher; filter, sort and paging happen on the
    already-scoped rows (fine for this data size; counts per status come from the same rows)."""
    q = (q or "").strip() or None
    rows = db.read(
        f"""
        MATCH (snd:Customer)-[:SENT]->(s:Shipment)-[:ADDRESSED_TO]->(rcv:Customer)
        WHERE {ACCESS}
          AND ($customerId IS NULL OR snd.customerId = $customerId OR rcv.customerId = $customerId)
          AND ($q IS NULL OR toString(s.shipmentId) = $q
               OR toLower(snd.firstName + ' ' + snd.lastName) CONTAINS toLower($q)
               OR toLower(rcv.firstName + ' ' + rcv.lastName) CONTAINS toLower($q))
        {CURRENT_STATUS}
        OPTIONAL MATCH (pay:Payment {{status: 'PAID'}})-[:PAYS_FOR]->(s)
        RETURN s.shipmentId AS shipmentId, toString(s.bookingDate) AS bookingDate,
               s.shipmentType AS shipmentType, s.weightKg AS weightKg, s.totalAmount AS totalAmount,
               coalesce(pay.amount, 0) AS paidAmount,
               snd.firstName + ' ' + snd.lastName AS sender, snd.city AS senderCity,
               rcv.firstName + ' ' + rcv.lastName AS receiver, rcv.city AS receiverCity,
               coalesce(cur.status, 'BOOKED') AS status, curBranch.name AS place, cur.eventTime AS since
        """,
        {**access_params(user), "q": q, "customerId": customer_id},
    )
    for r in rows:
        r["paymentState"] = payment_state(r["totalAmount"], r["paidAmount"])
    base = [r for r in rows if not payment or r["paymentState"] == payment]
    counts = {"ALL": len(base), "ACTIVE": sum(1 for r in base if r["status"] not in ACTIVE_EXCLUDE)}
    for st in config.VALID_STATUSES:
        counts[st] = sum(1 for r in base if r["status"] == st)
    if status == "ACTIVE":
        base = [r for r in base if r["status"] not in ACTIVE_EXCLUDE]
    elif status in config.VALID_STATUSES:
        base = [r for r in base if r["status"] == status]
    if sort == "amount":
        base.sort(key=lambda r: (-r["totalAmount"], -r["shipmentId"]))
    elif sort == "status":
        base.sort(key=lambda r: (STATUS_RANK.get(r["status"], 9), -r["shipmentId"]))
    else:
        base.sort(key=lambda r: (r["bookingDate"], r["shipmentId"]), reverse=True)
    total = len(base)
    page = max(page, 1)
    start = (page - 1) * page_size
    return {"items": base[start:start + page_size], "total": total, "page": page,
            "pageSize": page_size, "counts": counts}


def get_shipment(user: dict, shipment_id: int) -> dict:
    """G2, extended with branch, packages, payment and current status."""
    require_shipment_access(user, shipment_id)
    rows = db.read(
        f"""
        MATCH (snd:Customer)-[:SENT]->(s:Shipment {{shipmentId: $sid}})-[:ADDRESSED_TO]->(rcv:Customer)
        OPTIONAL MATCH (s)-[:BOOKED_AT]->(bk:Branch)
        {CURRENT_STATUS}
        CALL {{
          WITH s
          OPTIONAL MATCH (s)-[:CONTAINS]->(p:Package)
          WITH p ORDER BY p.packageId
          RETURN collect(CASE WHEN p IS NULL THEN null ELSE
                 {{packageId: p.packageId, description: p.description, dimensions: p.dimensions,
                  packageType: p.packageType, weightKg: p.weightKg}} END) AS packages
        }}
        OPTIONAL MATCH (pay:Payment)-[:PAYS_FOR]->(s)
        RETURN s.shipmentId AS shipmentId, toString(s.bookingDate) AS bookingDate,
               s.shipmentType AS shipmentType, s.weightKg AS weightKg, s.totalAmount AS totalAmount,
               snd {{.customerId, .firstName, .lastName, .city, .phone}} AS sender,
               rcv {{.customerId, .firstName, .lastName, .city, .phone}} AS receiver,
               bk.name AS bookedAt,
               coalesce(cur.status, 'BOOKED') AS status, curBranch.name AS place, cur.eventTime AS since,
               packages,
               CASE WHEN pay IS NULL THEN null ELSE
                 {{paymentId: pay.paymentId, amount: pay.amount, mode: pay.mode,
                  status: pay.status, paymentDate: toString(pay.paymentDate)}} END AS payment
        """,
        {"sid": shipment_id},
    )
    ship = rows[0]
    paid = ship["payment"]["amount"] if ship["payment"] and ship["payment"]["status"] == "PAID" else 0
    ship["paidAmount"] = paid
    ship["outstanding"] = round(ship["totalAmount"] - paid, 2)
    ship["paymentState"] = payment_state(ship["totalAmount"], paid)
    return ship


def status_board() -> list[dict]:
    """G3: current status of every shipment."""
    return db.read(
        """
        MATCH (s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(b:Branch)
        WHERE NOT (t)-[:NEXT]->()
        RETURN s.shipmentId AS shipment, t.status AS status, b.name AS place, t.eventTime AS since
        ORDER BY s.shipmentId
        """
    )


def rates() -> dict:
    return {k: {"base": b, "perKg": p} for k, (b, p) in config.RATE_CARD.items()}


def _create_payment(tx, shipment_id: int, data: dict) -> dict:
    return db.run(
        tx,
        """
        MATCH (s:Shipment {shipmentId: $sid})
        OPTIONAL MATCH (m:Payment)
        WITH s, coalesce(max(m.paymentId), 0) + 1 AS pid
        CREATE (p:Payment {paymentId: pid, amount: $amount, mode: $mode, status: $status, paymentDate: date()})
        CREATE (p)-[:PAYS_FOR]->(s)
        RETURN p.paymentId AS paymentId, p.amount AS amount, p.mode AS mode, p.status AS status,
               toString(p.paymentDate) AS paymentDate
        """,
        {"sid": shipment_id, **data},
    )[0]


def book_shipment(user: dict, data: dict) -> dict:
    """C2: shipment + packages + relationships + first BOOKED event (+ optional payment) in one write
    transaction. Ids are max+1 computed inside the same transaction."""
    packages = data["packages"]
    weight = round(sum(p["weightKg"] for p in packages), 2)
    amount = data.get("totalAmount")
    if amount is None:
        base, per_kg = config.RATE_CARD[data["shipmentType"]]
        amount = round(base + per_kg * weight, 2)
    emp_id = user["id"] if user["role"] == "STAFF" else None

    def work(tx):
        receiver = data.get("receiver")
        if receiver is None:
            found = db.run(tx, "MATCH (c:Customer {email: $e}) RETURN c.customerId AS id",
                           {"e": (data.get("receiverEmail") or "").strip().lower()})
            if not found:
                raise NotFound("No customer with that email.", code="RECEIVER_NOT_FOUND")
            receiver = found[0]["id"]
        ends = db.run(
            tx,
            """
            OPTIONAL MATCH (snd:Customer {customerId: $sender})
            OPTIONAL MATCH (rcv:Customer {customerId: $receiver})
            OPTIONAL MATCH (b:Branch {branchId: $branchId})
            RETURN snd IS NOT NULL AS hasSender, rcv IS NOT NULL AS hasReceiver, b IS NOT NULL AS hasBranch
            """,
            {**data, "receiver": receiver},
        )[0]
        if not ends["hasSender"]:
            raise NotFound(f"Sender customer {data['sender']} not found.")
        if not ends["hasReceiver"]:
            raise NotFound(f"Receiver customer {receiver} not found.", code="RECEIVER_NOT_FOUND")
        if not ends["hasBranch"]:
            raise NotFound(f"Branch {data['branchId']} not found.")
        rows = db.run(
            tx,
            """
            OPTIONAL MATCH (ms:Shipment)
            WITH coalesce(max(ms.shipmentId), 0) + 1 AS sid
            OPTIONAL MATCH (mp:Package)
            WITH sid, coalesce(max(mp.packageId), 0) AS maxPkg
            MATCH (snd:Customer {customerId: $sender}), (rcv:Customer {customerId: $receiver}),
                  (b:Branch {branchId: $branchId})
            CREATE (s:Shipment {shipmentId: sid, bookingDate: date(), shipmentType: $shipmentType,
                                weightKg: $weight, totalAmount: $amount})
            CREATE (snd)-[:SENT]->(s), (s)-[:ADDRESSED_TO]->(rcv), (s)-[:BOOKED_AT]->(b)
            CREATE (t:TrackingEvent {eventId: toString(sid) + '-1', shipmentId: sid, seq: 1,
                                     status: 'BOOKED', eventTime: datetime(), location: b.name})
            CREATE (s)-[:HAS_EVENT]->(t), (t)-[:AT]->(b)
            WITH s, t, maxPkg
            UNWIND range(0, size($packages) - 1) AS i
            WITH s, t, maxPkg, i, $packages[i] AS p
            CREATE (s)-[:CONTAINS]->(:Package {packageId: maxPkg + 1 + i, description: p.description,
                    dimensions: p.dimensions, packageType: p.packageType, weightKg: p.weightKg})
            WITH DISTINCT s, t
            OPTIONAL MATCH (e:Employee {employeeId: $emp})
            FOREACH (_ IN CASE WHEN e IS NULL THEN [] ELSE [1] END | CREATE (e)-[:LOGGED]->(t))
            RETURN s.shipmentId AS shipmentId
            """,
            {**data, "receiver": receiver, "weight": weight, "amount": amount, "emp": emp_id},
        )
        sid = rows[0]["shipmentId"]
        if data.get("payment") and user["role"] == "STAFF":
            _create_payment(tx, sid, {"amount": amount, **data["payment"]})
        return sid

    shipment_id = db.write(work)
    return {"shipmentId": shipment_id, "weightKg": weight, "totalAmount": amount,
            "packages": len(packages), "status": "BOOKED", "paid": bool(data.get("payment"))}


def record_payment(shipment_id: int, data: dict) -> dict:
    """One payment per shipment; the amount cannot exceed the outstanding balance."""
    def work(tx):
        ship = db.run(
            tx,
            """
            MATCH (s:Shipment {shipmentId: $sid})
            RETURN s.totalAmount AS total, EXISTS { (:Payment)-[:PAYS_FOR]->(s) } AS hasPayment
            """,
            {"sid": shipment_id},
        )
        if not ship:
            raise NotFound(f"Shipment {shipment_id} not found.")
        if ship[0]["hasPayment"]:
            raise Conflict("This shipment already has a payment.", code="PAYMENT_EXISTS")
        if data["amount"] > ship[0]["total"]:
            raise BadRequest(f"Amount cannot exceed the outstanding balance (₹{ship[0]['total']:g}).",
                             code="AMOUNT_TOO_HIGH")
        return _create_payment(tx, shipment_id, data)

    return db.write(work)
