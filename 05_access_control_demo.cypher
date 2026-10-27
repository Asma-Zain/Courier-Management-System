// ============================================================
// 05: access control (DCL equivalent)
// Needs Neo4j Desktop / Enterprise. Aura Free does NOT support
// custom roles, so if you use Aura, show this slide as "design"
// and say it was not executed.
// Run in the "system" database:  :use system
// Replace <choose-a-password> - never put real passwords in slides.
// ============================================================

CREATE ROLE trackingViewer IF NOT EXISTS;
GRANT ACCESS ON DATABASE neo4j TO trackingViewer;
GRANT MATCH {*} ON GRAPH neo4j NODES Shipment, TrackingEvent, Branch TO trackingViewer;
GRANT MATCH {*} ON GRAPH neo4j RELATIONSHIPS HAS_EVENT, NEXT, AT, ROUTE_TO TO trackingViewer;

CREATE USER viewer1 IF NOT EXISTS SET PASSWORD '<choose-a-password>' CHANGE NOT REQUIRED;
GRANT ROLE trackingViewer TO viewer1;

SHOW USERS;
SHOW ROLES;

// REVOKE example
REVOKE ROLE trackingViewer FROM viewer1;
