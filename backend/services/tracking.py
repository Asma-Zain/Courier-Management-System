from .. import db
from ..errors import Conflict, NotFound
from . import status as status_rules
from .common import require_shipment_access


def track(user: dict, shipment_id: int) -> list[dict]:
    """C3: ordered journey, access checked."""
    require_shipment_access(user, shipment_id)
    return db.read(
        """
        MATCH (s:Shipment {shipmentId: $sid})-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(b:Branch)
        OPTIONAL MATCH (e:Employee)-[:LOGGED]->(t)
        RETURN t.seq AS step, t.status AS status, t.eventTime AS time, b.name AS place,
               t.note AS note, e.firstName AS loggedBy
        ORDER BY t.seq
        """,
        {"sid": shipment_id},
    )


def _context(tx, shipment_id: int) -> dict:
    """History, current place and the places where delivery is acceptable (receiver's city)."""
    ship = db.run(tx, """
        MATCH (s:Shipment {shipmentId: $sid})-[:ADDRESSED_TO]->(r:Customer)
        OPTIONAL MATCH (b:Branch {city: r.city})
        RETURN r.city AS city, collect(b.name) AS deliveryPlaces""", {"sid": shipment_id})
    if not ship:
        raise NotFound(f"Shipment {shipment_id} not found.")
    events = db.run(tx, """
        MATCH (:Shipment {shipmentId: $sid})-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(b:Branch)
        RETURN t.status AS status, b.name AS place ORDER BY t.seq""", {"sid": shipment_id})
    history = [e["status"] for e in events]
    return {"history": history, "currentPlace": events[-1]["place"] if events else None,
            "deliveryPlaces": ship[0]["deliveryPlaces"], "receiverCity": ship[0]["city"],
            "allowed": status_rules.next_statuses(history)}


def next_statuses(shipment_id: int) -> dict:
    ctx = db.write(lambda tx: _context(tx, shipment_id))
    return {"current": ctx["history"][-1] if ctx["history"] else None, "allowed": ctx["allowed"],
            "currentPlace": ctx["currentPlace"], "deliveryPlaces": ctx["deliveryPlaces"]}


def add_event(user: dict, shipment_id: int, status: str, branch_name: str, note: str | None = None) -> dict:
    """C4: append an event; HAS_EVENT, NEXT, AT, LOGGED in one transaction. The status order is enforced here."""
    def work(tx):
        ctx = _context(tx, shipment_id)
        if not db.run(tx, "MATCH (b:Branch {name: $n}) RETURN b", {"n": branch_name}):
            raise NotFound(f"Branch or hub '{branch_name}' not found.")
        if status not in ctx["allowed"]:
            current = ctx["history"][-1] if ctx["history"] else "none"
            allowed = ctx["allowed"]
            msg = (f"Shipment is already {current}; no further events can be added." if not allowed else
                   f"Cannot move from {current} to {status}. Allowed next: {', '.join(allowed)}.")
            raise Conflict(msg, code="INVALID_TRANSITION", allowed=allowed, current=current)
        if status == "DELIVERED" and ctx["deliveryPlaces"] and branch_name not in ctx["deliveryPlaces"]:
            raise Conflict(f"Delivery must be recorded at the receiver's city ({ctx['receiverCity']}): "
                           + ", ".join(ctx["deliveryPlaces"]) + ".",
                           code="WRONG_DELIVERY_LOCATION", deliveryPlaces=ctx["deliveryPlaces"])
        return db.run(
            tx,
            """
            MATCH (s:Shipment {shipmentId: $sid}), (b:Branch {name: $branch}), (e:Employee {employeeId: $emp})
            OPTIONAL MATCH (s)-[:HAS_EVENT]->(last:TrackingEvent) WHERE NOT (last)-[:NEXT]->()
            CREATE (t:TrackingEvent {eventId: toString($sid) + '-' + toString(coalesce(last.seq, 0) + 1),
                                     shipmentId: $sid, seq: coalesce(last.seq, 0) + 1, status: $status,
                                     eventTime: datetime(), location: b.name, note: $note})
            CREATE (s)-[:HAS_EVENT]->(t), (t)-[:AT]->(b), (e)-[:LOGGED]->(t)
            FOREACH (_ IN CASE WHEN last IS NULL THEN [] ELSE [1] END | CREATE (last)-[:NEXT]->(t))
            RETURN t.eventId AS eventId, t.seq AS step, t.status AS status, b.name AS place
            """,
            {"sid": shipment_id, "branch": branch_name, "status": status, "emp": user["id"], "note": note},
        )
    rows = db.write(work)
    if not rows:
        raise NotFound("Shipment, branch or employee not found.")
    return rows[0]
