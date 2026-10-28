from .. import db


def overview() -> dict:
    """Staff Overview: KPIs, needs-attention list, recent activity, shipments waiting per location."""
    statuses = db.read("""
        MATCH (s:Shipment)
        OPTIONAL MATCH (s)-[:HAS_EVENT]->(t:TrackingEvent) WHERE NOT (t)-[:NEXT]->()
        OPTIONAL MATCH (pay:Payment {status: 'PAID'})-[:PAYS_FOR]->(s)
        RETURN s.shipmentId AS shipment, coalesce(t.status, 'BOOKED') AS status,
               s.totalAmount - coalesce(pay.amount, 0) AS outstanding""")
    active = [r for r in statuses if r["status"] not in ("DELIVERED", "CANCELLED")]
    kpis = {
        "active": len(active),
        "delayed": sum(1 for r in statuses if r["status"] == "DELAYED"),
        "outForDelivery": sum(1 for r in statuses if r["status"] == "OUT_FOR_DELIVERY"),
        "delivered": sum(1 for r in statuses if r["status"] == "DELIVERED"),
        "outstanding": sum(r["outstanding"] for r in statuses if r["status"] != "CANCELLED" and r["outstanding"] > 0),
    }
    attention = db.read("""
        MATCH (snd:Customer)-[:SENT]->(s:Shipment)-[:ADDRESSED_TO]->(rcv:Customer)
        OPTIONAL MATCH (s)-[:HAS_EVENT]->(t:TrackingEvent) WHERE NOT (t)-[:NEXT]->()
        OPTIONAL MATCH (t)-[:AT]->(b:Branch)
        OPTIONAL MATCH (pay:Payment {status: 'PAID'})-[:PAYS_FOR]->(s)
        WITH s, snd, rcv, t, b, s.totalAmount - coalesce(pay.amount, 0) AS due
        WHERE t.status = 'DELAYED' OR (due > 0 AND coalesce(t.status, 'BOOKED') <> 'CANCELLED')
        RETURN s.shipmentId AS shipmentId, coalesce(t.status, 'BOOKED') AS status, b.name AS place,
               rcv.firstName + ' ' + rcv.lastName AS receiver, due AS outstanding,
               t.status = 'DELAYED' AS delayed, t.eventTime AS since
        ORDER BY delayed DESC, shipmentId DESC LIMIT 10""")
    recent = db.read("""
        MATCH (s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(b:Branch)
        OPTIONAL MATCH (e:Employee)-[:LOGGED]->(t)
        RETURN s.shipmentId AS shipmentId, t.status AS status, b.name AS place, t.eventTime AS time,
               e.firstName AS loggedBy
        ORDER BY t.eventTime DESC LIMIT 8""")
    hubs = db.read("""
        MATCH (b:Branch)
        OPTIONAL MATCH (s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(b)
          WHERE NOT (t)-[:NEXT]->() AND NOT t.status IN ['DELIVERED', 'CANCELLED']
        RETURN b.branchId AS id, b.name AS name, b.kind AS kind, count(s) AS waiting ORDER BY id""")
    counts = db.read("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n")
    return {"kpis": kpis, "attention": attention, "recent": recent, "hubs": hubs,
            "system": {"connected": True, "counts": {c["label"]: c["n"] for c in counts}}}
