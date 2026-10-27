// ============================================================
// 04: technology-specific queries (graph traversals)
// Run one at a time. Use the "Graph" view where noted.
// ============================================================

// ---- G1. Parcel journey as a graph (use Graph view) ---------
MATCH (s:Shipment {shipmentId: 10000})-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(b:Branch)
RETURN s, t, b;

// ---- G2. Everything about one shipment ----------------------
MATCH (c:Customer)-[:SENT]->(s:Shipment {shipmentId: 10000})-[:ADDRESSED_TO]->(r:Customer)
OPTIONAL MATCH (s)-[:CONTAINS]->(p:Package)
OPTIONAL MATCH (pay:Payment)-[:PAYS_FOR]->(s)
RETURN c.firstName + ' ' + c.lastName AS sender,
       r.firstName + ' ' + r.lastName AS receiver,
       collect(p.description) AS packages,
       s.weightKg AS weightKg, s.totalAmount AS amount, pay.status AS payment;

// ---- G3. Current status of every shipment (last event in chain)
MATCH (s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(b:Branch)
WHERE NOT (t)-[:NEXT]->()
RETURN s.shipmentId AS shipment, t.status AS status, b.name AS place, t.eventTime AS since
ORDER BY s.shipmentId;

// ---- G4. Route with the fewest hops -------------------------
MATCH (a:Branch {name: 'Hyderabad Hub'}), (b:Branch {name: 'Coimbatore Hub'}),
      p = shortestPath((a)-[:ROUTE_TO*]-(b))
RETURN [n IN nodes(p) | n.name] AS route, length(p) AS hops;

// ---- G5. Route with the fewest kilometres (top 3, no plugin needed)
MATCH p = (a:Branch {name: 'Hyderabad Hub'})-[:ROUTE_TO*1..4]-(b:Branch {name: 'Coimbatore Hub'})
WHERE ALL(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))
WITH p, reduce(d = 0, r IN relationships(p) | d + r.km) AS km
RETURN [n IN nodes(p) | n.name] AS route, km
ORDER BY km
LIMIT 3;

// ---- G6. Hub delay impact: who is waiting on Chennai Hub? ---
MATCH (s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(h:Branch {name: 'Chennai Hub'}),
      (s)-[:ADDRESSED_TO]->(r:Customer)
WHERE NOT (t)-[:NEXT]->()
RETURN s.shipmentId AS shipment, t.status AS status,
       r.firstName + ' ' + r.lastName AS receiver, r.phone AS phone;

// ---- G7. Busiest locations by tracking events ---------------
MATCH (t:TrackingEvent)-[:AT]->(b:Branch)
RETURN b.name AS location, b.kind AS kind, count(t) AS events
ORDER BY events DESC, location;

// ---- G8. Customer network: who is 2 hops from Arun? ---------
MATCH (a:Customer {customerId: 1})-[:SENT]->(:Shipment)-[:ADDRESSED_TO]->(b:Customer)
      -[:SENT]->(:Shipment)-[:ADDRESSED_TO]->(c:Customer)
WHERE c <> a
RETURN DISTINCT a.firstName AS start, b.firstName AS via, c.firstName AS reaches;

// ---- G9. Delayed shipments with sender and receiver ---------
MATCH (snd:Customer)-[:SENT]->(s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent {status: 'DELAYED'}),
      (s)-[:ADDRESSED_TO]->(rcv:Customer)
WHERE NOT (t)-[:NEXT]->()
RETURN s.shipmentId AS shipment, snd.firstName AS sender, rcv.firstName AS receiver, t.location AS stuckAt;

// ---- G10. Branch performance: shipments and value -----------
MATCH (s:Shipment)-[:BOOKED_AT]->(b:Branch)
RETURN b.name AS branch, count(s) AS shipments, sum(s.totalAmount) AS value
ORDER BY value DESC;

// ---- G11. Employee activity ---------------------------------
MATCH (e:Employee)-[:LOGGED]->(t:TrackingEvent)
RETURN e.firstName + ' ' + e.lastName AS employee, e.jobRole AS role, count(t) AS events
ORDER BY events DESC;

// ---- G12. Payments and outstanding balance (LEFT JOIN equivalent)
MATCH (s:Shipment)
OPTIONAL MATCH (pay:Payment)-[:PAYS_FOR]->(s)
RETURN s.shipmentId AS shipment, s.totalAmount AS total,
       coalesce(pay.amount, 0) AS paid,
       s.totalAmount - coalesce(pay.amount, 0) AS outstanding
ORDER BY shipment;

// ---- G13. Packages per shipment, heavy packages -------------
MATCH (s:Shipment)-[:CONTAINS]->(p:Package)
RETURN s.shipmentId AS shipment, count(p) AS packages, sum(p.weightKg) AS packagesKg,
       s.weightKg AS shipmentKg, max(p.weightKg) AS heaviestPackageKg
ORDER BY shipment;

// ---- G14. Subquery 1: shipments heavier than the average ----
MATCH (s:Shipment)
WITH avg(s.weightKg) AS avgKg
MATCH (x:Shipment)
WHERE x.weightKg > avgKg
RETURN x.shipmentId AS shipment, x.weightKg AS kg, round(avgKg, 2) AS averageKg
ORDER BY kg DESC;

// ---- G15. Subquery 2: CALL { } per customer -----------------
MATCH (c:Customer)
CALL {
  WITH c
  MATCH (c)-[:SENT]->(s:Shipment)
  RETURN count(s) AS sent
}
CALL {
  WITH c
  MATCH (s2:Shipment)-[:ADDRESSED_TO]->(c)
  RETURN count(s2) AS received
}
RETURN c.firstName AS customer, sent, received
ORDER BY customer;

// ---- G16. Functions: string, date, numeric ------------------
MATCH (s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent)
WITH s, min(t.eventTime) AS first, max(t.eventTime) AS latest
RETURN s.shipmentId AS shipment, toUpper(s.shipmentType) AS type,
       toString(s.bookingDate) AS booked,
       round(duration.inSeconds(first, latest).seconds / 3600.0, 1) AS hoursTracked
ORDER BY shipment;
