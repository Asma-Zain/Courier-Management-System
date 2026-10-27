// ============================================================
// 02: sample data (same data as the Oracle version + hub network)
// Run the statements in order. Safe to re-run (uses MERGE).
// ============================================================

// ---- Branches and hubs (the transport network) -------------
UNWIND [
  {id: 1, name: 'Chennai Central Branch', kind: 'BRANCH', phone: '04440000001', street: '100 Mount Road',      city: 'Chennai',   state: 'Tamil Nadu', pincode: '600002'},
  {id: 2, name: 'Bengaluru City Branch',  kind: 'BRANCH', phone: '08040000002', street: '50 Residency Road',   city: 'Bengaluru', state: 'Karnataka',  pincode: '560025'},
  {id: 3, name: 'Chennai Hub',            kind: 'HUB', city: 'Chennai',    state: 'Tamil Nadu'},
  {id: 4, name: 'Hyderabad Hub',          kind: 'HUB', city: 'Hyderabad',  state: 'Telangana'},
  {id: 5, name: 'Coimbatore Hub',         kind: 'HUB', city: 'Coimbatore', state: 'Tamil Nadu'},
  {id: 6, name: 'Mumbai Hub',             kind: 'HUB', city: 'Mumbai',     state: 'Maharashtra'}
] AS r
MERGE (b:Branch {branchId: r.id})
SET b.name = r.name, b.kind = r.kind, b.phone = r.phone, b.street = r.street,
    b.city = r.city, b.state = r.state, b.pincode = r.pincode;

// ---- Routes between branches/hubs (km are approximate demo values)
UNWIND [
  {a: 1, b: 3, km: 12},  {a: 2, b: 3, km: 350}, {a: 2, b: 4, km: 570},
  {a: 2, b: 5, km: 365}, {a: 2, b: 6, km: 980}, {a: 3, b: 4, km: 630},
  {a: 3, b: 5, km: 500}, {a: 4, b: 6, km: 710}
] AS r
MATCH (x:Branch {branchId: r.a}), (y:Branch {branchId: r.b})
MERGE (x)-[:ROUTE_TO {km: r.km}]->(y);

// ---- Employees ----------------------------------------------
UNWIND [
  {id: 1, branch: 1, first: 'Karthik', last: 'R', email: 'karthik@courier.com', phone: '9000000001', role: 'Branch Manager',     joined: '2024-06-01'},
  {id: 2, branch: 1, first: 'Divya',   last: 'S', email: 'divya@courier.com',   phone: '9000000002', role: 'Tracking Executive', joined: '2025-01-10'},
  {id: 3, branch: 2, first: 'Naveen',  last: 'P', email: 'naveen@courier.com',  phone: '9000000003', role: 'Tracking Executive', joined: '2025-03-15'}
] AS r
MERGE (e:Employee {employeeId: r.id})
SET e.firstName = r.first, e.lastName = r.last, e.email = r.email,
    e.phone = r.phone, e.jobRole = r.role, e.joinDate = date(r.joined)
WITH e, r
MATCH (b:Branch {branchId: r.branch})
MERGE (e)-[:WORKS_AT]->(b);

// ---- Customers ----------------------------------------------
UNWIND [
  {id: 1, first: 'Arun',  last: 'Kumar',  email: 'arun@example.com',  phone: '9876500001', street: '12 Lake Road',  city: 'Chennai',    state: 'Tamil Nadu', pincode: '600042'},
  {id: 2, first: 'Priya', last: 'Sharma', email: 'priya@example.com', phone: '9876500002', street: '8 Park Street', city: 'Bengaluru',  state: 'Karnataka',  pincode: '560001'},
  {id: 3, first: 'Rahul', last: 'Verma',  email: 'rahul@example.com', phone: '9876500003', street: '22 MG Road',    city: 'Hyderabad',  state: 'Telangana',  pincode: '500001'},
  {id: 4, first: 'Meera', last: 'Nair',   email: 'meera@example.com', phone: '9876500004', street: '17 Beach Road', city: 'Coimbatore', state: 'Tamil Nadu', pincode: '641001'}
] AS r
MERGE (c:Customer {customerId: r.id})
SET c.firstName = r.first, c.lastName = r.last, c.email = r.email, c.phone = r.phone,
    c.street = r.street, c.city = r.city, c.state = r.state, c.pincode = r.pincode;

// ---- Shipments (sender, receiver and booking branch become relationships)
UNWIND [
  {id: 1,     sender: 1, receiver: 2, branch: 1, booked: '2026-09-25', type: 'STANDARD',  weight: 2.50, amount: 150.00},
  {id: 2,     sender: 2, receiver: 3, branch: 2, booked: '2026-09-26', type: 'EXPRESS',   weight: 4.00, amount: 225.00},
  {id: 3,     sender: 3, receiver: 4, branch: 2, booked: '2026-09-27', type: 'OVERNIGHT', weight: 1.50, amount: 215.00},
  {id: 4,     sender: 4, receiver: 1, branch: 1, booked: '2026-09-28', type: 'STANDARD',  weight: 3.00, amount: 150.00},
  {id: 10000, sender: 1, receiver: 4, branch: 1, booked: '2026-10-03', type: 'EXPRESS',   weight: 2.75, amount: 190.00}
] AS r
MERGE (s:Shipment {shipmentId: r.id})
SET s.bookingDate = date(r.booked), s.shipmentType = r.type,
    s.weightKg = r.weight, s.totalAmount = r.amount
WITH s, r
MATCH (snd:Customer {customerId: r.sender}), (rcv:Customer {customerId: r.receiver}), (b:Branch {branchId: r.branch})
MERGE (snd)-[:SENT]->(s)
MERGE (s)-[:ADDRESSED_TO]->(rcv)
MERGE (s)-[:BOOKED_AT]->(b);

// ---- Packages (many per shipment) ---------------------------
UNWIND [
  {id: 1,     ship: 1,     descr: 'Documents',              dims: '30x20x5 cm',  type: 'Envelope', weight: 1.50},
  {id: 2,     ship: 1,     descr: 'Books',                  dims: '25x20x6 cm',  type: 'Box',      weight: 1.00},
  {id: 3,     ship: 2,     descr: 'Electronic accessories', dims: '40x30x15 cm', type: 'Box',      weight: 4.00},
  {id: 4,     ship: 3,     descr: 'Clothing',               dims: '25x20x10 cm', type: 'Parcel',   weight: 1.50},
  {id: 5,     ship: 4,     descr: 'Household items',        dims: '35x25x15 cm', type: 'Box',      weight: 3.00},
  {id: 50000, ship: 10000, descr: 'Important documents',    dims: '30x20x8 cm',  type: 'Envelope', weight: 1.25},
  {id: 50001, ship: 10000, descr: 'Books',                  dims: '25x20x10 cm', type: 'Box',      weight: 1.50}
] AS r
MATCH (s:Shipment {shipmentId: r.ship})
MERGE (p:Package {packageId: r.id})
SET p.description = r.descr, p.dimensions = r.dims, p.packageType = r.type, p.weightKg = r.weight
MERGE (s)-[:CONTAINS]->(p);

// ---- Payments -----------------------------------------------
UNWIND [
  {id: 1,     ship: 1,     amount: 150.00, mode: 'UPI',        status: 'PAID', paid: '2026-09-25'},
  {id: 2,     ship: 2,     amount: 225.00, mode: 'CARD',       status: 'PAID', paid: '2026-09-26'},
  {id: 3,     ship: 3,     amount: 215.00, mode: 'NETBANKING', status: 'PAID', paid: '2026-09-27'},
  {id: 4,     ship: 4,     amount: 150.00, mode: 'CASH',       status: 'PAID', paid: '2026-09-28'},
  {id: 90000, ship: 10000, amount: 190.00, mode: 'UPI',        status: 'PAID', paid: '2026-10-03'}
] AS r
MATCH (s:Shipment {shipmentId: r.ship})
MERGE (p:Payment {paymentId: r.id})
SET p.amount = r.amount, p.mode = r.mode, p.status = r.status, p.paymentDate = date(r.paid)
MERGE (p)-[:PAYS_FOR]->(s);

// ---- Tracking events (a linked list per shipment) -----------
UNWIND [
  {ship: 1,     seq: 1, status: 'BOOKED',           ts: '2026-09-25T09:00:00+05:30', loc: 'Chennai',               branch: 1, emp: 1},
  {ship: 1,     seq: 2, status: 'PICKED_UP',        ts: '2026-09-25T13:30:00+05:30', loc: 'Chennai',               branch: 1, emp: 2},
  {ship: 1,     seq: 3, status: 'IN_TRANSIT',       ts: '2026-09-26T08:15:00+05:30', loc: 'Chennai Hub',           branch: 3, emp: 2},
  {ship: 2,     seq: 1, status: 'BOOKED',           ts: '2026-09-26T10:00:00+05:30', loc: 'Bengaluru',             branch: 2, emp: 3},
  {ship: 2,     seq: 2, status: 'AT_BRANCH',        ts: '2026-09-26T14:20:00+05:30', loc: 'Bengaluru City Branch', branch: 2, emp: 3},
  {ship: 2,     seq: 3, status: 'OUT_FOR_DELIVERY', ts: '2026-09-27T09:10:00+05:30', loc: 'Bengaluru',             branch: 2, emp: 3},
  {ship: 3,     seq: 1, status: 'BOOKED',           ts: '2026-09-27T11:00:00+05:30', loc: 'Hyderabad',             branch: 4, emp: 3},
  {ship: 3,     seq: 2, status: 'IN_TRANSIT',       ts: '2026-09-27T18:30:00+05:30', loc: 'Hyderabad Hub',         branch: 4, emp: 3},
  {ship: 4,     seq: 1, status: 'BOOKED',           ts: '2026-09-28T10:15:00+05:30', loc: 'Chennai',               branch: 1, emp: 1},
  {ship: 4,     seq: 2, status: 'DELAYED',          ts: '2026-09-29T17:45:00+05:30', loc: 'Chennai Hub',           branch: 3, emp: 2},
  {ship: 10000, seq: 1, status: 'PICKED_UP',        ts: '2026-10-03T10:30:00+05:30', loc: 'Chennai Central',       branch: 1, emp: 2},
  {ship: 10000, seq: 2, status: 'IN_TRANSIT',       ts: '2026-10-03T15:00:00+05:30', loc: 'Chennai Hub',           branch: 3, emp: 2}
] AS r
MATCH (s:Shipment {shipmentId: r.ship}), (b:Branch {branchId: r.branch}), (e:Employee {employeeId: r.emp})
MERGE (t:TrackingEvent {eventId: toString(r.ship) + '-' + toString(r.seq)})
SET t.shipmentId = r.ship, t.seq = r.seq, t.status = r.status,
    t.eventTime = datetime(r.ts), t.location = r.loc
MERGE (s)-[:HAS_EVENT]->(t)
MERGE (t)-[:AT]->(b)
MERGE (e)-[:LOGGED]->(t);

// ---- Chain each shipment's events in order: (event1)-[:NEXT]->(event2)
MATCH (s:Shipment)-[:HAS_EVENT]->(a:TrackingEvent), (s)-[:HAS_EVENT]->(b:TrackingEvent)
WHERE b.seq = a.seq + 1
MERGE (a)-[:NEXT]->(b);

// ---- Check: should return 6 Branch, 4 Customer, 3 Employee, 5 Shipment,
//      7 Package, 5 Payment, 12 TrackingEvent
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS nodes ORDER BY label;
