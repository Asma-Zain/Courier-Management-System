from neo4j.exceptions import ConstraintError

from .. import db
from ..errors import Conflict, NotFound

RETURN_CUSTOMER = """RETURN c.customerId AS customerId, c.firstName AS firstName, c.lastName AS lastName,
       c.email AS email, c.phone AS phone, c.street AS street, c.city AS city,
       c.state AS state, c.pincode AS pincode"""


def list_customers() -> list[dict]:
    return db.read(f"MATCH (c:Customer) {RETURN_CUSTOMER} ORDER BY customerId")


def get_customer(customer_id: int) -> dict:
    rows = db.read(f"MATCH (c:Customer {{customerId: $id}}) {RETURN_CUSTOMER}", {"id": customer_id})
    if not rows:
        raise NotFound(f"Customer {customer_id} not found.")
    return rows[0]


def lookup_by_email(email: str) -> dict:
    """Minimal public-to-logged-in view (id and name only) so a sender can pick a receiver."""
    rows = db.read(
        "MATCH (c:Customer {email: $email}) "
        "RETURN c.customerId AS customerId, c.firstName + ' ' + c.lastName AS name, c.city AS city",
        {"email": email.strip().lower()},
    )
    if not rows:
        raise NotFound("No customer with that email.")
    return rows[0]


def create_customer(data: dict) -> dict:
    """C1. Id is max+1 inside the write transaction unless the caller supplies one.
    The uniqueness constraints turn duplicates into ConstraintError (C7 demo)."""
    explicit = data.get("customerId") is not None

    def work(tx):
        return db.run(
            tx,
            f"""
            OPTIONAL MATCH (m:Customer)
            WITH coalesce(max(m.customerId), 0) + 1 AS nextId
            CREATE (c:Customer {{customerId: coalesce($customerId, nextId),
                                firstName: $firstName, lastName: $lastName, email: $email,
                                phone: $phone, street: $street, city: $city,
                                state: $state, pincode: $pincode}})
            {RETURN_CUSTOMER}
            """,
            data,
        )[0]

    attempts = 1 if explicit else 3  # concurrent max+1 clash -> retry with a fresh id
    for attempt in range(attempts):
        try:
            return db.write(work)
        except ConstraintError:
            if attempt == attempts - 1:
                raise
    raise Conflict("Could not allocate a customer id.")  # pragma: no cover


def update_customer(customer_id: int, changes: dict) -> dict:
    """C5. Only phone and address fields can change."""
    if not changes:
        return get_customer(customer_id)
    rows = db.write(lambda tx: db.run(
        tx, f"MATCH (c:Customer {{customerId: $id}}) SET c += $changes {RETURN_CUSTOMER}",
        {"id": customer_id, "changes": changes}))
    if not rows:
        raise NotFound(f"Customer {customer_id} not found.")
    return rows[0]


def delete_customer(customer_id: int) -> None:
    """C6. Refuses (409) when the customer is linked to any shipment."""
    def work(tx):
        rows = db.run(
            tx,
            """
            MATCH (c:Customer {customerId: $id})
            RETURN EXISTS { (c)-[:SENT]->(:Shipment) } OR EXISTS { (:Shipment)-[:ADDRESSED_TO]->(c) } AS linked
            """,
            {"id": customer_id},
        )
        if not rows:
            raise NotFound(f"Customer {customer_id} not found.")
        if rows[0]["linked"]:
            raise Conflict("This customer has shipments (sent or received) and cannot be deleted.")
        db.run(tx, "MATCH (c:Customer {customerId: $id}) DETACH DELETE c", {"id": customer_id})
    db.write(work)
