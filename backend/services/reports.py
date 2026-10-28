from .. import db

QUERIES = {
    # G7
    "busiest-locations": """
        MATCH (t:TrackingEvent)-[:AT]->(b:Branch)
        RETURN b.name AS location, b.kind AS kind, count(t) AS events
        ORDER BY events DESC, location""",
    # G9
    "delayed": """
        MATCH (snd:Customer)-[:SENT]->(s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent {status: 'DELAYED'}),
              (s)-[:ADDRESSED_TO]->(rcv:Customer)
        WHERE NOT (t)-[:NEXT]->()
        RETURN s.shipmentId AS shipment, snd.firstName AS sender, rcv.firstName AS receiver, t.location AS stuckAt
        ORDER BY shipment""",
    # G10
    "branch-performance": """
        MATCH (s:Shipment)-[:BOOKED_AT]->(b:Branch)
        RETURN b.name AS branch, count(s) AS shipments, sum(s.totalAmount) AS value
        ORDER BY value DESC""",
    # G11
    "employee-activity": """
        MATCH (e:Employee)-[:LOGGED]->(t:TrackingEvent)
        RETURN e.firstName + ' ' + e.lastName AS employee, e.jobRole AS role, count(t) AS events
        ORDER BY events DESC, employee""",
    # G12 (only PAID payments count as paid, so PENDING ones stay outstanding)
    "payments": """
        MATCH (s:Shipment)
        OPTIONAL MATCH (pay:Payment)-[:PAYS_FOR]->(s)
        WITH s, pay, CASE WHEN pay.status = 'PAID' THEN pay.amount ELSE 0 END AS paid
        RETURN s.shipmentId AS shipment, s.totalAmount AS total, paid,
               s.totalAmount - paid AS outstanding, pay.status AS paymentStatus
        ORDER BY shipment""",
    # G13
    "packages-per-shipment": """
        MATCH (s:Shipment)-[:CONTAINS]->(p:Package)
        RETURN s.shipmentId AS shipment, count(p) AS packages, sum(p.weightKg) AS packagesKg,
               s.weightKg AS shipmentKg, max(p.weightKg) AS heaviestPackageKg
        ORDER BY shipment""",
    # G14
    "heavier-than-average": """
        MATCH (s:Shipment)
        WITH avg(s.weightKg) AS avgKg
        MATCH (x:Shipment)
        WHERE x.weightKg > avgKg
        RETURN x.shipmentId AS shipment, x.weightKg AS kg, round(avgKg, 2) AS averageKg
        ORDER BY kg DESC""",
    # G15
    "customer-activity": """
        MATCH (c:Customer)
        CALL { WITH c MATCH (c)-[:SENT]->(s:Shipment) RETURN count(s) AS sent }
        CALL { WITH c MATCH (s2:Shipment)-[:ADDRESSED_TO]->(c) RETURN count(s2) AS received }
        RETURN c.firstName AS customer, sent, received
        ORDER BY customer""",
    # G16
    "tracking-duration": """
        MATCH (s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent)
        WITH s, min(t.eventTime) AS first, max(t.eventTime) AS latest
        RETURN s.shipmentId AS shipment, toUpper(s.shipmentType) AS type,
               toString(s.bookingDate) AS booked,
               round(duration.inSeconds(first, latest).seconds / 3600.0, 1) AS hoursTracked
        ORDER BY shipment""",
}


def run_report(name: str) -> list[dict]:
    return db.read(QUERIES[name])


def customer_network(customer_id: int) -> list[dict]:
    """G8: who is two hops away from this customer."""
    return db.read(
        """
        MATCH (a:Customer {customerId: $cid})-[:SENT]->(:Shipment)-[:ADDRESSED_TO]->(b:Customer)
              -[:SENT]->(:Shipment)-[:ADDRESSED_TO]->(c:Customer)
        WHERE c <> a
        RETURN DISTINCT a.firstName AS start, b.firstName AS via, c.firstName AS reaches
        ORDER BY via, reaches""",
        {"cid": customer_id},
    )
