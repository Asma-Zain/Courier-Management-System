from .. import db


def dashboard() -> dict:
    counts = db.read("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS nodes ORDER BY label")
    statuses = db.read(
        """
        MATCH (s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent) WHERE NOT (t)-[:NEXT]->()
        RETURN t.status AS status, count(s) AS shipments ORDER BY shipments DESC, status
        """
    )
    outstanding = db.read(
        """
        MATCH (s:Shipment)
        OPTIONAL MATCH (pay:Payment {status: 'PAID'})-[:PAYS_FOR]->(s)
        WITH s, s.totalAmount - coalesce(pay.amount, 0) AS due
        WHERE due > 0
        RETURN s.shipmentId AS shipment, due AS outstanding ORDER BY shipment
        """
    )
    return {
        "counts": counts,
        "statuses": statuses,
        "outstanding": {"total": sum(r["outstanding"] for r in outstanding), "shipments": outstanding},
    }
