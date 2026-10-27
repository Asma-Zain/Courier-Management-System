// ============================================================
// COURIER TRACKING SYSTEM - NEO4J
// 01: constraints and indexes (run once, before loading data)
// Works on Neo4j 5.x (Aura Free and Neo4j Desktop)
// ============================================================

// Uniqueness constraints = PRIMARY KEY / UNIQUE in the Oracle version
CREATE CONSTRAINT customer_id_unique IF NOT EXISTS FOR (c:Customer) REQUIRE c.customerId IS UNIQUE;
CREATE CONSTRAINT customer_email_unique IF NOT EXISTS FOR (c:Customer) REQUIRE c.email IS UNIQUE;
CREATE CONSTRAINT branch_id_unique IF NOT EXISTS FOR (b:Branch) REQUIRE b.branchId IS UNIQUE;
CREATE CONSTRAINT branch_name_unique IF NOT EXISTS FOR (b:Branch) REQUIRE b.name IS UNIQUE;
CREATE CONSTRAINT employee_id_unique IF NOT EXISTS FOR (e:Employee) REQUIRE e.employeeId IS UNIQUE;
CREATE CONSTRAINT employee_email_unique IF NOT EXISTS FOR (e:Employee) REQUIRE e.email IS UNIQUE;
CREATE CONSTRAINT shipment_id_unique IF NOT EXISTS FOR (s:Shipment) REQUIRE s.shipmentId IS UNIQUE;
CREATE CONSTRAINT package_id_unique IF NOT EXISTS FOR (p:Package) REQUIRE p.packageId IS UNIQUE;
CREATE CONSTRAINT payment_id_unique IF NOT EXISTS FOR (p:Payment) REQUIRE p.paymentId IS UNIQUE;
CREATE CONSTRAINT event_id_unique IF NOT EXISTS FOR (t:TrackingEvent) REQUIRE t.eventId IS UNIQUE;

// Indexes for common lookups (like the Oracle indexes)
CREATE INDEX tracking_status_idx IF NOT EXISTS FOR (t:TrackingEvent) ON (t.status);
CREATE INDEX shipment_type_idx IF NOT EXISTS FOR (s:Shipment) ON (s.shipmentType);

// NOTE: NOT NULL / CHECK constraints (property existence) are Enterprise-only
// in Neo4j, so this project enforces them in the Python app instead.
