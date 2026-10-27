// ============================================================
// 03: core operations (CRUD) - run one statement at a time
// and take a screenshot of each result
// ============================================================

// ---- C1. CREATE a customer ----------------------------------
MERGE (c:Customer {customerId: 5})
SET c.firstName = 'Sneha', c.lastName = 'Iyer', c.email = 'sneha@example.com',
    c.phone = '9876500005', c.street = '5 Hill View', c.city = 'Chennai',
    c.state = 'Tamil Nadu', c.pincode = '600020'
RETURN c;

// ---- C2. CREATE a shipment with two packages ----------------
MATCH (snd:Customer {customerId: 5}), (rcv:Customer {customerId: 2}), (b:Branch {branchId: 1})
CREATE (s:Shipment {shipmentId: 10001, bookingDate: date('2026-10-27'), shipmentType: 'STANDARD',
                    weightKg: 3.50, totalAmount: 150.00})
CREATE (snd)-[:SENT]->(s), (s)-[:ADDRESSED_TO]->(rcv), (s)-[:BOOKED_AT]->(b)
CREATE (s)-[:CONTAINS]->(p1:Package {packageId: 50002, description: 'Gift box', dimensions: '30x30x15 cm', packageType: 'Box', weightKg: 2.00})
CREATE (s)-[:CONTAINS]->(p2:Package {packageId: 50003, description: 'Greeting cards', dimensions: '25x15x5 cm', packageType: 'Envelope', weightKg: 1.50})
RETURN s, snd, rcv, b, p1, p2;

// ---- C3. READ: track one shipment ---------------------------
MATCH (s:Shipment {shipmentId: 1})-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(b:Branch)
RETURN s.shipmentId AS shipment, t.seq AS step, t.status AS status, t.eventTime AS time, b.name AS place
ORDER BY t.seq;

// ---- C4. UPDATE: append a new tracking event ----------------
MATCH (s:Shipment {shipmentId: 10000})-[:HAS_EVENT]->(last:TrackingEvent)
WHERE NOT (last)-[:NEXT]->()
MATCH (b:Branch {name: 'Hyderabad Hub'}), (e:Employee {employeeId: 2})
CREATE (t:TrackingEvent {eventId: toString(s.shipmentId) + '-' + toString(last.seq + 1),
                         shipmentId: s.shipmentId, seq: last.seq + 1,
                         status: 'AT_BRANCH', eventTime: datetime(), location: b.name})
CREATE (s)-[:HAS_EVENT]->(t), (last)-[:NEXT]->(t), (t)-[:AT]->(b), (e)-[:LOGGED]->(t)
RETURN t.eventId AS newEvent, t.status AS status, b.name AS place;

// ---- C5. UPDATE: change a property --------------------------
MATCH (c:Customer {customerId: 1})
SET c.phone = '9876500099'
RETURN c.firstName AS name, c.phone AS newPhone;

// ---- C6. DELETE: remove the test customer and everything linked
MATCH (c:Customer {customerId: 5})-[:SENT]->(s:Shipment {shipmentId: 10001})
OPTIONAL MATCH (s)-[:CONTAINS]->(p:Package)
DETACH DELETE p, s;

MATCH (c:Customer {customerId: 5})
DETACH DELETE c;

// ---- C7. Integrity: this MUST fail (duplicate key) ----------
CREATE (:Customer {customerId: 1, firstName: 'Duplicate', lastName: 'Test', email: 'dup@example.com'});

// ---- C8. CLEAN UP: undo C4 and C5 so the queries in 04 give the expected results
MATCH (:Shipment {shipmentId: 10000})-[:HAS_EVENT]->(t:TrackingEvent {eventId: '10000-3'})
DETACH DELETE t;

MATCH (c:Customer {customerId: 1})
SET c.phone = '9876500001'
RETURN c.firstName AS name, c.phone AS phone;
