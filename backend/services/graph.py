from .. import db
from .common import require_shipment_access


def shipment_graph(user: dict, shipment_id: int) -> dict:
    """G1 style journey: Shipment, TrackingEvents, Branches, with NEXT links."""
    require_shipment_access(user, shipment_id)
    rows = db.read(
        """
        MATCH (s:Shipment {shipmentId: $sid})-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(b:Branch)
        OPTIONAL MATCH (t)-[:NEXT]->(n:TrackingEvent)
        RETURN s.shipmentId AS sid, s.shipmentType AS stype,
               t.eventId AS eventId, t.seq AS seq, t.status AS status, t.eventTime AS time,
               b.branchId AS branchId, b.name AS branch, b.kind AS kind, n.eventId AS nextId
        ORDER BY t.seq
        """,
        {"sid": shipment_id},
    )
    nodes, edges, seen = [], [], set()

    def add(node):
        if node["id"] not in seen:
            seen.add(node["id"])
            nodes.append(node)

    add({"id": f"shipment:{shipment_id}", "label": f"Shipment {shipment_id}", "group": "Shipment"})
    for r in rows:
        eid, bid = f"event:{r['eventId']}", f"branch:{r['branchId']}"
        add({"id": eid, "label": f"{r['seq']}. {r['status'].replace('_', ' ').capitalize()}",
             "group": "TrackingEvent", "title": r["time"], "status": r["status"]})
        add({"id": bid, "label": r["branch"], "group": r["kind"] or "Branch"})
        edges.append({"from": f"shipment:{shipment_id}", "to": eid, "label": "HAS_EVENT"})
        edges.append({"from": eid, "to": bid, "label": "AT"})
        if r["nextId"]:
            edges.append({"from": eid, "to": f"event:{r['nextId']}", "label": "NEXT"})
    return {"nodes": nodes, "edges": edges}


def network_graph() -> dict:
    branches = db.read("MATCH (b:Branch) RETURN b.branchId AS id, b.name AS name, b.kind AS kind ORDER BY id")
    routes = db.read(
        "MATCH (a:Branch)-[r:ROUTE_TO]->(b:Branch) RETURN a.branchId AS a, b.branchId AS b, r.km AS km"
    )
    return {
        "nodes": [{"id": f"branch:{b['id']}", "label": b["name"], "group": b["kind"]} for b in branches],
        "edges": [{"from": f"branch:{r['a']}", "to": f"branch:{r['b']}", "label": f"{r['km']} km", "km": r["km"]}
                  for r in routes],
    }
