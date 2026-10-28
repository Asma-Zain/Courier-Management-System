from .. import config, db
from ..errors import BadRequest, Conflict, NotFound
from .common import ACCESS, access_params, require_shipment_access

# current status = the TrackingEvent with no outgoing NEXT
CURRENT_STATUS = """
OPTIONAL MATCH (s)-[:HAS_EVENT]->(cur:TrackingEvent) WHERE NOT (cur)-[:NEXT]->()
OPTIONAL MATCH (cur)-[:AT]->(curBranch:Branch)
"""


def list_shipments(user: dict) -> list[dict]:
    return db.read(
        f"""
        MATCH (snd:Customer)-[:SENT]->(s:Shipment)-[:ADDRESSED_TO]->(rcv:Customer)
        WHERE {ACCESS}
        {CURRENT_STATUS}
        RETURN s.shipmentId AS shipmentId, toString(s.bookingDate) AS bookingDate,
               s.shipmentType AS shipmentType, s.weightKg AS weightKg, s.totalAmount AS totalAmount,
               snd.firstName + ' ' + snd.lastName AS sender,
               rcv.firstName + ' ' + rcv.lastName AS receiver,
               snd.city AS senderCity, rcv.city AS receiverCity,
               cur.status AS status, curBranch.name AS place, toString(cur.eventTime) AS since
        ORDER BY shipmentId
        """,
        access_params(user),
    )


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
               cur.status AS status, curBranch.name AS place, toString(cur.eventTime) AS since,
               packages,
               CASE WHEN pay IS NULL THEN null ELSE
                 {{paymentId: pay.paymentId, amount: pay.amount, mode: pay.mode,
                  status: pay.status, paymentDate: toString(pay.paymentDate)}} END AS payment
        """,
        {"sid": shipment_id},
    )
    return rows[0]


def status_board() -> list[dict]:
    """G3: current status of every shipment."""
    return db.read(
        """
        MATCH (s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(b:Branch)
        WHERE NOT (t)-[:NEXT]->()
        RETURN s.shipmentId AS shipment, t.status AS status, b.name AS place, toString(t.eventTime) AS since
        ORDER BY s.shipmentId
        """
    )


def book_shipment(user: dict, data: dict) -> dict:
    """C2: shipment + packages + relationships + first BOOKED event in one write transaction.
    Ids are max+1 computed inside the same transaction."""
    packages = data["packages"]
    weight = round(sum(p["weightKg"] for p in packages), 2)
    amount = data.get("totalAmount")
    if amount is None:
        base, per_kg = config.RATE_CARD[data["shipmentType"]]
        amount = round(base + per_kg * weight, 2)
    emp_id = user["id"] if user["role"] == "STAFF" else None

    def work(tx):
        ends = db.run(
            tx,
            """
            OPTIONAL MATCH (snd:Customer {customerId: $sender})
            OPTIONAL MATCH (rcv:Customer {customerId: $receiver})
            OPTIONAL MATCH (b:Branch {branchId: $branchId})
            RETURN snd IS NOT NULL AS hasSender, rcv IS NOT NULL AS hasReceiver, b IS NOT NULL AS hasBranch
            """,
            data,
        )[0]
        if not ends["hasSender"]:
            raise NotFound(f"Sender customer {data['sender']} not found.")
        if not ends["hasReceiver"]:
            raise NotFound(f"Receiver customer {data['receiver']} not found.")
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
            {**data, "weight": weight, "amount": amount, "emp": emp_id},
        )
        return rows[0]["shipmentId"]

    shipment_id = db.write(work)
    return {"shipmentId": shipment_id, "weightKg": weight, "totalAmount": amount,
            "packages": len(packages), "status": "BOOKED"}


def record_payment(shipment_id: int, data: dict) -> dict:
    """One payment per shipment; amount cannot exceed the shipment total."""
    def work(tx):
        ship = db.run(
            tx,
            """
            MATCH (s:Shipment {shipmentId: $sid})
            RETURN s.totalAmount AS total, EXISTS { (:Payment)-[:PAYS_FOR]->(s) } AS paid
            """,
            {"sid": shipment_id},
        )
        if not ship:
            raise NotFound(f"Shipment {shipment_id} not found.")
        if ship[0]["paid"]:
            raise Conflict("This shipment already has a payment.")
        if data["amount"] > ship[0]["total"]:
            raise BadRequest(f"Amount cannot exceed the shipment total ({ship[0]['total']}).")
        return db.run(
            tx,
            """
            MATCH (s:Shipment {shipmentId: $sid})
            OPTIONAL MATCH (m:Payment)
            WITH s, coalesce(max(m.paymentId), 0) + 1 AS pid
            CREATE (p:Payment {paymentId: pid, amount: $amount, mode: $mode, status: $status,
                               paymentDate: date()})
            CREATE (p)-[:PAYS_FOR]->(s)
            RETURN p.paymentId AS paymentId, p.amount AS amount, p.mode AS mode, p.status AS status,
                   toString(p.paymentDate) AS paymentDate
            """,
            {"sid": shipment_id, **data},
        )[0]

    return db.write(work)
