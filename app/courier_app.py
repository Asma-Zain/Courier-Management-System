"""Courier Tracking System - Neo4j demo application (command line).

Roles
  STAFF    = anyone whose email is in an Employee node. Can track any
             shipment, add tracking events and see hub impact.
  CUSTOMER = anyone whose email is in a Customer node. Can only see
             shipments they sent or are receiving.

Demo login only: it matches on email and has no password. A real system
would use proper authentication.
"""
import os
import sys

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

VALID_STATUSES = {
    "BOOKED", "PICKED_UP", "IN_TRANSIT", "AT_BRANCH",
    "OUT_FOR_DELIVERY", "DELIVERED", "DELAYED", "CANCELLED",
}

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
)
DB = os.getenv("NEO4J_DATABASE", "neo4j")


def read(query, params=None):
    with driver.session(database=DB) as session:
        return session.execute_read(lambda tx: [r.data() for r in tx.run(query, params or {})])


def write(query, params=None):
    with driver.session(database=DB) as session:
        return session.execute_write(lambda tx: [r.data() for r in tx.run(query, params or {})])


# ---------------------------------------------------------------- login
def login(email):
    staff = read(
        "MATCH (e:Employee {email: $email}) "
        "RETURN e.employeeId AS id, e.firstName AS name, e.jobRole AS jobRole",
        {"email": email},
    )
    if staff:
        return {"role": "STAFF", **staff[0]}
    cust = read(
        "MATCH (c:Customer {email: $email}) RETURN c.customerId AS id, c.firstName AS name",
        {"email": email},
    )
    if cust:
        return {"role": "CUSTOMER", **cust[0]}
    return None


# ----------------------------------------------------------- operations
def track(user, shipment_id):
    """Journey of one shipment. Customers only see their own."""
    cid = user["id"] if user["role"] == "CUSTOMER" else -1
    return read(
        """
        MATCH (s:Shipment {shipmentId: $sid})
        WHERE $role = 'STAFF'
           OR EXISTS { MATCH (:Customer {customerId: $cid})-[:SENT]->(s) }
           OR EXISTS { MATCH (s)-[:ADDRESSED_TO]->(:Customer {customerId: $cid}) }
        MATCH (s)-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(b:Branch)
        RETURN t.seq AS step, t.status AS status, toString(t.eventTime) AS time, b.name AS place
        ORDER BY t.seq
        """,
        {"sid": shipment_id, "role": user["role"], "cid": cid},
    )


def add_event(user, shipment_id, status, branch_name):
    """Append a tracking event to the end of the shipment's chain. Staff only."""
    if user["role"] != "STAFF":
        raise PermissionError("Only staff can add tracking events.")
    status = status.strip().upper()
    if status not in VALID_STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(sorted(VALID_STATUSES))}")
    rows = write(
        """
        MATCH (s:Shipment {shipmentId: $sid})-[:HAS_EVENT]->(last:TrackingEvent)
        WHERE NOT (last)-[:NEXT]->()
        MATCH (b:Branch {name: $branch}), (e:Employee {employeeId: $emp})
        CREATE (t:TrackingEvent {eventId: toString($sid) + '-' + toString(last.seq + 1),
                                 shipmentId: $sid, seq: last.seq + 1, status: $status,
                                 eventTime: datetime(), location: b.name})
        CREATE (s)-[:HAS_EVENT]->(t), (last)-[:NEXT]->(t), (t)-[:AT]->(b), (e)-[:LOGGED]->(t)
        RETURN t.eventId AS eventId
        """,
        {"sid": shipment_id, "status": status, "branch": branch_name, "emp": user["id"]},
    )
    if not rows:
        raise LookupError("Shipment, branch or employee not found.")
    return rows[0]["eventId"]


def best_route(from_name, to_name):
    """Fewest-km route between two branches/hubs."""
    return read(
        """
        MATCH p = (a:Branch {name: $a})-[:ROUTE_TO*1..5]-(b:Branch {name: $b})
        WHERE ALL(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))
        WITH p, reduce(d = 0, r IN relationships(p) | d + r.km) AS km
        RETURN [n IN nodes(p) | n.name] AS route, km
        ORDER BY km LIMIT 1
        """,
        {"a": from_name, "b": to_name},
    )


def hub_impact(user, hub_name):
    """Shipments whose latest event is at the given hub, with receiver. Staff only."""
    if user["role"] != "STAFF":
        raise PermissionError("Only staff can run hub impact reports.")
    return read(
        """
        MATCH (s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(:Branch {name: $hub}),
              (s)-[:ADDRESSED_TO]->(r:Customer)
        WHERE NOT (t)-[:NEXT]->()
        RETURN s.shipmentId AS shipment, t.status AS status,
               r.firstName + ' ' + r.lastName AS receiver
        ORDER BY shipment
        """,
        {"hub": hub_name},
    )


# ------------------------------------------------------------------ menu
def show(rows):
    if not rows:
        print("  (nothing found, or you do not have access)")
    for row in rows:
        print("  ", row)


def menu(user):
    while True:
        print(f"\n--- Courier Tracking (Neo4j) | {user['name']} [{user['role']}] ---")
        print("1) Track a shipment")
        print("2) Find shortest route between two hubs")
        if user["role"] == "STAFF":
            print("3) Add a tracking event")
            print("4) Hub impact report")
        print("0) Exit")
        choice = input("Choose: ").strip()
        try:
            if choice == "1":
                show(track(user, int(input("Shipment id: "))))
            elif choice == "2":
                show(best_route(input("From (e.g. Hyderabad Hub): ").strip(),
                                input("To (e.g. Coimbatore Hub): ").strip()))
            elif choice == "3":
                sid = int(input("Shipment id: "))
                status = input("Status: ")
                place = input("Branch/hub name: ").strip()
                print("  added event", add_event(user, sid, status, place))
            elif choice == "4":
                show(hub_impact(user, input("Hub name (e.g. Chennai Hub): ").strip()))
            elif choice == "0":
                return
            else:
                print("  Unknown option.")
        except (ValueError, PermissionError, LookupError) as err:
            print("  Error:", err)


if __name__ == "__main__":
    with driver:
        email = input("Login email: ").strip().lower()
        who = login(email)
        if not who:
            sys.exit("No account with that email.")
        menu(who)
