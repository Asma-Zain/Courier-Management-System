# Page / button to API endpoint to Cypher

All Cypher is parameterised and lives in `backend/services/`. "Q" ids refer to `03_core_operations.cypher` (C1-C8) and `04_graph_queries.cypher` (G1-G16).

| Page | Button / action | Endpoint | Role | Cypher (service file) | Q |
| --- | --- | --- | --- | --- | --- |
| Login | Log in | `POST /api/auth/login` | any | `MATCH (e:Employee {email:$email})` then `MATCH (c:Customer {email:$email})` (`services/auth.py`) | CLI login |
| Header | Log out | `POST /api/auth/logout` | any | none (clears cookie) | |
| All pages | (header) | `GET /api/auth/me` | any | `MATCH (e:Employee {employeeId:$id})` / `MATCH (c:Customer {customerId:$id})` | |
| Dashboard | page load (counts) | `GET /api/dashboard` | staff | `MATCH (n) RETURN labels(n)[0], count(*)`; statuses: `MATCH (s)-[:HAS_EVENT]->(t) WHERE NOT (t)-[:NEXT]->() RETURN t.status, count(s)`; outstanding: shipment total minus PAID `Payment` (`services/dashboard.py`) | G3, G12 |
| Dashboard | status board | `GET /api/shipments/status` | staff | `MATCH (s)-[:HAS_EVENT]->(t)-[:AT]->(b) WHERE NOT (t)-[:NEXT]->()` (`services/shipments.py`) | G3 |
| Dashboard | shipment list | `GET /api/shipments` | any (customers: own only) | `MATCH (snd)-[:SENT]->(s)-[:ADDRESSED_TO]->(rcv) WHERE $role='STAFF' OR EXISTS{...SENT...} OR EXISTS{...ADDRESSED_TO...}` + current-status `OPTIONAL MATCH` | CLI track |
| Dashboard (customer) | My profile | `GET /api/customers/{id}` | customer (own) | `MATCH (c:Customer {customerId:$id})` (`services/customers.py`) | |
| Track | Track | `GET /api/shipments/{id}` | any (access checked) | access check `RETURN <EXISTS{} access> ` then G2 query extended with packages (`collect`), payment, current status | G2 |
| Track | Track (timeline) | `GET /api/shipments/{id}/track` | any (access checked) | `MATCH (s {shipmentId})-[:HAS_EVENT]->(t)-[:AT]->(b) RETURN ... ORDER BY t.seq` (`services/tracking.py`) | C3 |
| Track | Track (graph picture) | `GET /api/graph/shipment/{id}` | any (access checked) | `MATCH (s)-[:HAS_EVENT]->(t)-[:AT]->(b) OPTIONAL MATCH (t)-[:NEXT]->(n)` (`services/graph.py`) | G1 |
| Track | Add event | `POST /api/shipments/{id}/events` | staff | existence checks, then `CREATE (t:TrackingEvent ...) CREATE (s)-[:HAS_EVENT]->(t), (last)-[:NEXT]->(t), (t)-[:AT]->(b), (e)-[:LOGGED]->(t)` in one transaction | C4 |
| Track | Record payment | `POST /api/shipments/{id}/payment` | staff | check total / existing payment, then `CREATE (p:Payment ...)-[:PAYS_FOR]->(s)`; id = max+1 (`services/shipments.py`) | |
| Book | Book shipment | `POST /api/shipments` | any (customers send as themselves) | one write tx: existence checks, `CREATE (s:Shipment)`, `SENT`, `ADDRESSED_TO`, `BOOKED_AT`, first `BOOKED` event, `UNWIND` packages `CREATE (s)-[:CONTAINS]->(:Package)`; ids = max+1 | C2 |
| Book | (receiver field) | `GET /api/customers/lookup?email=` | any | `MATCH (c:Customer {email:$email}) RETURN id, name, city` | |
| Book / Routes / Track | dropdowns | `GET /api/branches` | any | `MATCH (b:Branch) RETURN ...` (`services/branches.py`) | |
| Book (staff) | sender dropdown | `GET /api/customers` | staff | `MATCH (c:Customer) RETURN ...` | |
| Routes | Find routes | `GET /api/routes/fewest-hops` | any | `shortestPath((a)-[:ROUTE_TO*]-(b))` (`services/routes.py`) | G4 |
| Routes | Find routes | `GET /api/routes/fewest-km` | any | `(a)-[:ROUTE_TO*1..5]-(b)` + `single()` no-repeat filter + `reduce()` km, `ORDER BY km LIMIT 3` | G5 |
| Routes | network picture | `GET /api/graph/network` | any | `MATCH (a)-[r:ROUTE_TO]->(b) RETURN a, b, r.km` (`services/graph.py`) | |
| Hub impact | Show impact | `GET /api/hubs/{name}/impact` | staff | `MATCH (s)-[:HAS_EVENT]->(t)-[:AT]->(h {name:$hub}), (s)-[:ADDRESSED_TO]->(r) WHERE NOT (t)-[:NEXT]->()` | G6 |
| Reports | Busiest locations | `GET /api/reports/busiest-locations` | staff | `MATCH (t)-[:AT]->(b) RETURN b.name, count(t)` | G7 |
| Reports | Customer network | `GET /api/reports/customer-network?customer_id=` | staff | 2-hop `SENT/ADDRESSED_TO` chain, `DISTINCT` | G8 |
| Reports | Delayed | `GET /api/reports/delayed` | staff | `(t:TrackingEvent {status:'DELAYED'}) WHERE NOT (t)-[:NEXT]->()` | G9 |
| Reports | Branch performance | `GET /api/reports/branch-performance` | staff | `MATCH (s)-[:BOOKED_AT]->(b) RETURN count(s), sum(s.totalAmount)` | G10 |
| Reports | Employee activity | `GET /api/reports/employee-activity` | staff | `MATCH (e)-[:LOGGED]->(t) RETURN count(t)` | G11 |
| Reports | Payments | `GET /api/reports/payments` | staff | `OPTIONAL MATCH (pay)-[:PAYS_FOR]->(s)`, paid only when `status='PAID'` | G12 |
| Reports | Packages per shipment | `GET /api/reports/packages-per-shipment` | staff | `MATCH (s)-[:CONTAINS]->(p) RETURN count, sum, max` | G13 |
| Reports | Heavier than average | `GET /api/reports/heavier-than-average` | staff | `WITH avg(s.weightKg) AS avgKg MATCH (x) WHERE x.weightKg > avgKg` | G14 |
| Reports | Sent / received | `GET /api/reports/customer-activity` | staff | two `CALL { WITH c ... }` subqueries | G15 |
| Reports | Hours tracked | `GET /api/reports/tracking-duration` | staff | `min/max(t.eventTime)`, `duration.inSeconds` | G16 |
| Customers | list | `GET /api/customers` | staff | `MATCH (c:Customer) RETURN ...` | |
| Customers | Create customer | `POST /api/customers` | staff | `CREATE (c:Customer {customerId: coalesce($customerId, max+1), ...})`; duplicate -> `ConstraintError` -> 409 | C1, C7 |
| Customers | Save changes (edit) | `PATCH /api/customers/{id}` | staff / own | `MATCH (c {customerId:$id}) SET c += $changes` (phone and address only) | C5 |
| Customers | Delete | `DELETE /api/customers/{id}` | staff | check `SENT` / `ADDRESSED_TO` links, 409 if any, else `DETACH DELETE c` | C6 |
