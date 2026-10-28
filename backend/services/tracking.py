from .. import config, db
from ..errors import Conflict, NotFound
from .common import ACCESS, access_params, require_shipment_access


def track(user: dict, shipment_id: int) -> list[dict]:
    """C3: ordered journey, access checked."""
    require_shipment_access(user, shipment_id)
    return db.read(
        """
        MATCH (s:Shipment {shipmentId: $sid})-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(b:Branch)
        RETURN t.seq AS step, t.status AS status, toString(t.eventTime) AS time, b.name AS place
        ORDER BY t.seq
        """,
        {"sid": shipment_id},
    )


def add_event(user: dict, shipment_id: int, status: str, branch_name: str) -> dict:
    """C4: append an event; HAS_EVENT, NEXT, AT, LOGGED created in one transaction."""
    def work(tx):
        check = db.run(
            tx,
            """
            OPTIONAL MATCH (s:Shipment {shipmentId: $sid})
            OPTIONAL MATCH (b:Branch {name: $branch})
            OPTIONAL MATCH (s)-[:HAS_EVENT]->(last:TrackingEvent) WHERE NOT (last)-[:NEXT]->()
            RETURN s IS NOT NULL AS hasShipment, b IS NOT NULL AS hasBranch, last.status AS lastStatus
            """,
            {"sid": shipment_id, "branch": branch_name},
        )[0]
        if not check["hasShipment"]:
            raise NotFound(f"Shipment {shipment_id} not found.")
        if not check["hasBranch"]:
            raise NotFound(f"Branch or hub '{branch_name}' not found.")
        if check["lastStatus"] in config.TERMINAL_STATUSES:
            raise Conflict(f"Shipment is already {check['lastStatus']}; no further events can be added.")
        return db.run(
            tx,
            """
            MATCH (s:Shipment {shipmentId: $sid}), (b:Branch {name: $branch}),
                  (e:Employee {employeeId: $emp})
            OPTIONAL MATCH (s)-[:HAS_EVENT]->(last:TrackingEvent) WHERE NOT (last)-[:NEXT]->()
            CREATE (t:TrackingEvent {eventId: toString($sid) + '-' + toString(coalesce(last.seq, 0) + 1),
                                     shipmentId: $sid, seq: coalesce(last.seq, 0) + 1, status: $status,
                                     eventTime: datetime(), location: b.name})
            CREATE (s)-[:HAS_EVENT]->(t), (t)-[:AT]->(b), (e)-[:LOGGED]->(t)
            FOREACH (_ IN CASE WHEN last IS NULL THEN [] ELSE [1] END | CREATE (last)-[:NEXT]->(t))
            RETURN t.eventId AS eventId, t.seq AS step, t.status AS status, b.name AS place
            """,
            {"sid": shipment_id, "branch": branch_name, "status": status, "emp": user["id"]},
        )
    rows = db.write(work)
    if not rows:
        raise NotFound("Shipment, branch or employee not found.")
    return rows[0]
