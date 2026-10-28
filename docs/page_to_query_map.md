# Page, tab and button to endpoint to Cypher

All Cypher is parameterised and lives in `backend/services/`. "Q" ids refer to `03_core_operations.cypher` (C1-C8) and `04_graph_queries.cypher` (G1-G16). The reports page shows each G-query under **Show query**.

## Everyone

| Page (URL) | Action | Endpoint | Cypher (service file) | Q |
| --- | --- | --- | --- | --- |
| Login (`/login`) | Log in | `POST /api/auth/login` | `MATCH (e:Employee {email:$email})` then `MATCH (c:Customer {email:$email})` (`services/auth.py`) | CLI login |
| Login | demo chips / docs link | `GET /api/auth/config` | none | |
| Every page (header) | session / account menu | `GET /api/auth/me` | `MATCH (e:Employee {employeeId:$id}) OPTIONAL MATCH (e)-[:WORKS_AT]->(b)` / `MATCH (c:Customer {customerId:$id})` | |
| Account menu | Log out | `POST /api/auth/logout` | none (clears cookie) | |
| Header search | shipment ID | navigates to `/shipments/{id}` (a name opens `/shipments?q=`) | none | |
| Home (customer, `/`) | "Your parcels in progress" | `GET /api/shipments?status=ACTIVE&pageSize=3` | list query below, scoped by `EXISTS {}` | |
| Shipments (`/shipments`) | list, search, status chips, sort, paging | `GET /api/shipments?q&status&payment&sort&page&pageSize` | `MATCH (snd)-[:SENT]->(s)-[:ADDRESSED_TO]->(rcv) WHERE $role='STAFF' OR EXISTS{(:Customer {customerId:$cid})-[:SENT]->(s)} OR EXISTS{(s)-[:ADDRESSED_TO]->(:Customer {customerId:$cid})}` + name search + current status (`OPTIONAL MATCH (s)-[:HAS_EVENT]->(cur) WHERE NOT (cur)-[:NEXT]->()`) + PAID payment; filter/sort/page in Python (`services/shipments.py`) | G3 |
| Shipment detail (`/shipments/{id}`) | page load | `GET /api/shipments/{id}` | access check (`RETURN <EXISTS{} access>`), then G2 extended with packages (`collect`), payment, current status | G2 |
| Shipment detail > Journey | timeline and route | `GET /api/shipments/{id}/track` | `MATCH (s {shipmentId})-[:HAS_EVENT]->(t)-[:AT]->(b) OPTIONAL MATCH (e:Employee)-[:LOGGED]->(t) ... ORDER BY t.seq` (`services/tracking.py`) | C3 |
| Shipment detail > Graph | graph view | `GET /api/graph/shipment/{id}` | `MATCH (s)-[:HAS_EVENT]->(t)-[:AT]->(b) OPTIONAL MATCH (t)-[:NEXT]->(n)` (`services/graph.py`) | G1 |
| Book a shipment (`/shipments/new`) step 1 | receiver email check | `GET /api/customers/lookup?email=` (rate limited) | `MATCH (c:Customer {email:$email})`; customers get only `{exists, displayName}` | |
| Book step 1 (staff) | sender list | `GET /api/customers` | `MATCH (c:Customer) ...` | |
| Book step 3 | price preview | `GET /api/shipments/rates` | none (rate card in `config.py`) | |
| Book step 3 | Book shipment | `POST /api/shipments` | one write tx: existence checks, `CREATE (s:Shipment)`, `SENT`, `ADDRESSED_TO`, `BOOKED_AT`, first `BOOKED` event, `UNWIND` packages `CREATE (s)-[:CONTAINS]->(:Package)`, optional `Payment` (staff); ids = `max+1` | C2 |
| Book (dropdowns) | branches | `GET /api/branches` | `MATCH (b:Branch) RETURN ...` | |
| Account (`/account`) | profile | `GET /api/auth/me`, `GET /api/customers/{id}` (customer) | see above | |
| Account (customer) | Save changes | `PATCH /api/customers/{id}` | `MATCH (c {customerId:$id}) SET c += $changes` (phone and address only) | C5 |

## Staff only

| Page (URL) | Action | Endpoint | Cypher (service file) | Q |
| --- | --- | --- | --- | --- |
| Overview (`/`) | KPI tiles, needs attention, recent activity, hub map, system strip | `GET /api/overview` | current status per shipment + PAID payments; attention: `t.status='DELAYED' OR due>0`; recent: `MATCH (s)-[:HAS_EVENT]->(t)-[:AT]->(b) OPTIONAL MATCH (e)-[:LOGGED]->(t) ORDER BY t.eventTime DESC LIMIT 8`; waiting per place: `OPTIONAL MATCH ... WHERE NOT (t)-[:NEXT]->() AND NOT t.status IN [...]` (`services/overview.py`) | G3, G12 |
| Overview | hub map | `GET /api/graph/network` | `MATCH (a:Branch)-[r:ROUTE_TO]->(b:Branch) RETURN a, b, r.km` | |
| Shipment detail | actions: valid statuses | `GET /api/shipments/{id}/next-statuses` | history `MATCH (s)-[:HAS_EVENT]->(t) ... ORDER BY t.seq` then the status-order rules in `services/status.py`; receiver city branches for delivery | |
| Shipment detail | Add event | `POST /api/shipments/{id}/events` | order and delivery-place checks, then `CREATE (t:TrackingEvent ...) CREATE (s)-[:HAS_EVENT]->(t), (last)-[:NEXT]->(t), (t)-[:AT]->(b), (e)-[:LOGGED]->(t)` in one tx | C4 |
| Shipment detail | Record payment | `POST /api/shipments/{id}/payment` | check total and existing payment, then `CREATE (p:Payment ...)-[:PAYS_FOR]->(s)`; id = `max+1` | |
| Shipment detail | Print label | none (print stylesheet) | none | |
| Network (`/network`) > Routes | From / To (auto) | `GET /api/routes/fewest-hops` | `shortestPath((a)-[:ROUTE_TO*]-(b))` (`services/routes.py`) | G4 |
| Network > Routes | From / To (auto) | `GET /api/routes/fewest-km` | `(a)-[:ROUTE_TO*1..5]-(b)` + `single()` no-repeat filter + `reduce()` km, `ORDER BY km LIMIT 3` | G5 |
| Network | map | `GET /api/graph/network` | see above | |
| Network > Hub impact | hub select or map click | `GET /api/hubs/{name}/impact` | `MATCH (s)-[:HAS_EVENT]->(t)-[:AT]->(h {name:$hub}), (s)-[:ADDRESSED_TO]->(r) WHERE NOT (t)-[:NEXT]->()` | G6 |
| Customers (`/customers`) | list, search | `GET /api/customers` | `MATCH (c:Customer) CALL { WITH c MATCH (s:Shipment) WHERE EXISTS{(c)-[:SENT]->(s)} OR EXISTS{(s)-[:ADDRESSED_TO]->(c)} RETURN count(s) } ...` (`services/customers.py`) | |
| Customers | Add customer (modal) | `POST /api/customers` | `CREATE (c:Customer {customerId: coalesce($customerId, max+1), ...})`; duplicate id or email gives `ConstraintError` -> 409 | C1, C7 |
| Customer (`/customers/{id}`) | profile | `GET /api/customers/{id}` | `MATCH (c:Customer {customerId:$id})` | |
| Customer | their shipments | `GET /api/shipments?customerId=` | list query with `snd.customerId=$customerId OR rcv.customerId=$customerId` | |
| Customer | Edit (modal) | `PATCH /api/customers/{id}` | `SET c += $changes` | C5 |
| Customer | Delete (confirm dialog) | `DELETE /api/customers/{id}` | check `SENT` / `ADDRESSED_TO`, 409 if any, else `DETACH DELETE c` | C6 |
| Reports (`/reports/{slug}`) | catalogue | `GET /api/reports` | none (registry in `services/reports.py`) | |
| Reports | run (auto on selection) | `GET /api/reports/{slug}` | see the G-queries below | |
| Reports | Show query | (text from the catalogue) | the Cypher of the selected report | |
| Reports | Export CSV / Print | none (browser) | none | |

### Reports

| Report (group) | slug | Query |
| --- | --- | --- |
| Busiest locations (Operations) | `busiest-locations` | G7 `MATCH (t)-[:AT]->(b) RETURN b.name, count(t)` |
| Customer network (People) | `customer-network` | G8 two-hop `SENT/ADDRESSED_TO` chain, `DISTINCT` |
| Delayed shipments (Operations) | `delayed` | G9 `(t {status:'DELAYED'}) WHERE NOT (t)-[:NEXT]->()` |
| Branch performance (Operations) | `branch-performance` | G10 `MATCH (s)-[:BOOKED_AT]->(b) RETURN count(s), sum(s.totalAmount)` |
| Employee activity (People) | `employee-activity` | G11 `MATCH (e)-[:LOGGED]->(t) RETURN count(t)` |
| Payments and outstanding (Money) | `payments` | G12 `OPTIONAL MATCH (pay)-[:PAYS_FOR]->(s)`, paid only when `status='PAID'` |
| Packages per shipment (Shipments) | `packages-per-shipment` | G13 `count`, `sum`, `max` per shipment |
| Heavier than average (Shipments) | `heavier-than-average` | G14 `WITH avg(s.weightKg) AS avgKg MATCH (x) WHERE x.weightKg > avgKg` |
| Customer activity (People) | `customer-activity` | G15 two `CALL { WITH c ... }` subqueries |
| Hours tracked (Shipments) | `tracking-duration` | G16 `min/max(t.eventTime)`, `duration.inSeconds` |

## Operational endpoints (no page)

`GET /healthz` (process alive), `GET /readyz` (runs `RETURN 1` against Neo4j), `GET /docs` (development only unless `ENABLE_DOCS=true`).
