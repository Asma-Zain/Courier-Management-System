"""Report registry: one entry per report with its academic query id (G7-G16), friendly column
labels/formats for the UI and the Cypher text shown in the "Show query" panel."""
from .. import db
from ..errors import NotFound


def _r(id_, slug, group, title, description, columns, cypher, chart=None, param=None):
    return {"id": id_, "slug": slug, "group": group, "title": title, "description": description,
            "columns": [{"key": k, "label": lbl, "format": f} for k, lbl, f in columns],
            "chart": chart, "param": param, "cypher": " ".join(cypher.split()).strip()}


REPORTS = [
    _r("G7", "busiest-locations", "Operations", "Busiest locations",
       "Tracking events recorded at each branch and hub.",
       [("location", "Location", "text"), ("kind", "Type", "kind"), ("events", "Events", "int")],
       "", {"label": "location", "value": "events", "format": "int"}),
    _r("G9", "delayed", "Operations", "Delayed shipments",
       "Shipments whose current status is Delayed, with who is waiting.",
       [("shipment", "Shipment", "shipment"), ("sender", "Sender", "text"), ("receiver", "Receiver", "text"),
        ("stuckAt", "Stuck at", "text")], ""),
    _r("G10", "branch-performance", "Operations", "Branch performance",
       "Shipments booked at each branch and their total value.",
       [("branch", "Branch", "text"), ("shipments", "Shipments", "int"), ("value", "Value", "money")],
       "", {"label": "branch", "value": "value", "format": "money"}),
    _r("G11", "employee-activity", "People", "Employee activity",
       "Tracking events logged by each employee.",
       [("employee", "Employee", "text"), ("role", "Role", "text"), ("events", "Events logged", "int")],
       "", {"label": "employee", "value": "events", "format": "int"}),
    _r("G15", "customer-activity", "People", "Customer activity",
       "How many shipments each customer sent and received.",
       [("customer", "Customer", "text"), ("sent", "Sent", "int"), ("received", "Received", "int")], ""),
    _r("G8", "customer-network", "People", "Customer network",
       "Who a customer can reach in two hops: they sent to someone, who sent to someone else.",
       [("start", "Customer", "text"), ("via", "Via", "text"), ("reaches", "Reaches", "text")], "",
       None, "customer"),
    _r("G12", "payments", "Money", "Payments and outstanding",
       "Shipment total, amount paid (PAID payments only) and what is still due.",
       [("shipment", "Shipment", "shipment"), ("total", "Total", "money"), ("paid", "Paid", "money"),
        ("outstanding", "Outstanding", "money"), ("paymentStatus", "Payment", "text")], ""),
    _r("G13", "packages-per-shipment", "Shipments", "Packages per shipment",
       "Package count, combined weight and the heaviest package of each shipment.",
       [("shipment", "Shipment", "shipment"), ("packages", "Packages", "int"),
        ("packagesKg", "Total weight", "kg"), ("heaviestPackageKg", "Heaviest package", "kg")], ""),
    _r("G14", "heavier-than-average", "Shipments", "Heavier than average",
       "Shipments above the average shipment weight.",
       [("shipment", "Shipment", "shipment"), ("kg", "Weight", "kg"), ("averageKg", "Average weight", "kg")], ""),
    _r("G16", "tracking-duration", "Shipments", "Hours tracked",
       "Time between the first and the latest tracking event of each shipment.",
       [("shipment", "Shipment", "shipment"), ("type", "Type", "title"), ("booked", "Booked", "date"),
        ("hoursTracked", "Hours tracked", "hours")], ""),
]

CYPHER = {
    "busiest-locations": """MATCH (t:TrackingEvent)-[:AT]->(b:Branch)
RETURN b.name AS location, b.kind AS kind, count(t) AS events
ORDER BY events DESC, location""",
    "delayed": """MATCH (snd:Customer)-[:SENT]->(s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent {status: 'DELAYED'}),
      (s)-[:ADDRESSED_TO]->(rcv:Customer)
WHERE NOT (t)-[:NEXT]->()
RETURN s.shipmentId AS shipment, snd.firstName + ' ' + snd.lastName AS sender,
       rcv.firstName + ' ' + rcv.lastName AS receiver, t.location AS stuckAt
ORDER BY shipment""",
    "branch-performance": """MATCH (s:Shipment)-[:BOOKED_AT]->(b:Branch)
RETURN b.name AS branch, count(s) AS shipments, sum(s.totalAmount) AS value
ORDER BY value DESC""",
    "employee-activity": """MATCH (e:Employee)-[:LOGGED]->(t:TrackingEvent)
RETURN e.firstName + ' ' + e.lastName AS employee, e.jobRole AS role, count(t) AS events
ORDER BY events DESC, employee""",
    "payments": """MATCH (s:Shipment)
OPTIONAL MATCH (pay:Payment)-[:PAYS_FOR]->(s)
WITH s, pay, CASE WHEN pay.status = 'PAID' THEN pay.amount ELSE 0 END AS paid
RETURN s.shipmentId AS shipment, s.totalAmount AS total, paid,
       s.totalAmount - paid AS outstanding, pay.status AS paymentStatus
ORDER BY shipment""",
    "packages-per-shipment": """MATCH (s:Shipment)-[:CONTAINS]->(p:Package)
RETURN s.shipmentId AS shipment, count(p) AS packages, sum(p.weightKg) AS packagesKg,
       s.weightKg AS shipmentKg, max(p.weightKg) AS heaviestPackageKg
ORDER BY shipment""",
    "heavier-than-average": """MATCH (s:Shipment)
WITH avg(s.weightKg) AS avgKg
MATCH (x:Shipment)
WHERE x.weightKg > avgKg
RETURN x.shipmentId AS shipment, x.weightKg AS kg, round(avgKg, 2) AS averageKg
ORDER BY kg DESC""",
    "customer-activity": """MATCH (c:Customer)
CALL { WITH c MATCH (c)-[:SENT]->(s:Shipment) RETURN count(s) AS sent }
CALL { WITH c MATCH (s2:Shipment)-[:ADDRESSED_TO]->(c) RETURN count(s2) AS received }
RETURN c.firstName + ' ' + c.lastName AS customer, sent, received
ORDER BY customer""",
    "customer-network": """MATCH (a:Customer {customerId: $customerId})-[:SENT]->(:Shipment)-[:ADDRESSED_TO]->(b:Customer)
      -[:SENT]->(:Shipment)-[:ADDRESSED_TO]->(c:Customer)
WHERE c <> a
RETURN DISTINCT a.firstName + ' ' + a.lastName AS start, b.firstName + ' ' + b.lastName AS via,
       c.firstName + ' ' + c.lastName AS reaches
ORDER BY via, reaches""",
    "tracking-duration": """MATCH (s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent)
WITH s, min(t.eventTime) AS first, max(t.eventTime) AS latest
RETURN s.shipmentId AS shipment, s.shipmentType AS type,
       toString(s.bookingDate) AS booked,
       round(duration.inSeconds(first, latest).seconds / 3600.0, 1) AS hoursTracked
ORDER BY shipment""",
}
for _rep in REPORTS:
    _rep["cypher"] = CYPHER[_rep["slug"]]
BY_SLUG = {r["slug"]: r for r in REPORTS}


def metadata() -> list[dict]:
    return REPORTS


def run_report(slug: str, customer_id: int | None = None) -> dict:
    rep = BY_SLUG.get(slug)
    if not rep:
        raise NotFound(f"Report '{slug}' not found.")
    params = {"customerId": customer_id or 1} if rep["param"] else {}
    return {"report": rep, "rows": db.read(rep["cypher"], params)}
