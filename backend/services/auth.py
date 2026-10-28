import time

from .. import db

_CACHE: dict = {}
TTL = 30  # seconds; a deleted account stops working within this window


def login(email: str) -> dict | None:
    email = email.strip().lower()
    staff = db.read(
        "MATCH (e:Employee {email: $email}) OPTIONAL MATCH (e)-[:WORKS_AT]->(b:Branch) "
        "RETURN e.employeeId AS id, e.firstName AS name, e.lastName AS lastName, e.jobRole AS jobRole, "
        "e.email AS email, b.name AS branch",
        {"email": email},
    )
    if staff:
        return {"role": "STAFF", **staff[0]}
    cust = db.read(
        "MATCH (c:Customer {email: $email}) "
        "RETURN c.customerId AS id, c.firstName AS name, c.lastName AS lastName, c.email AS email",
        {"email": email},
    )
    if cust:
        return {"role": "CUSTOMER", **cust[0]}
    return None


def load_user(role: str, user_id: int) -> dict | None:
    hit = _CACHE.get((role, user_id))
    if hit and time.monotonic() - hit[0] < TTL:
        return hit[1]
    user = _load_user(role, user_id)
    _CACHE[(role, user_id)] = (time.monotonic(), user)
    return user


def _load_user(role: str, user_id: int) -> dict | None:
    if role == "STAFF":
        rows = db.read(
            "MATCH (e:Employee {employeeId: $id}) OPTIONAL MATCH (e)-[:WORKS_AT]->(b:Branch) "
            "RETURN e.employeeId AS id, e.firstName AS name, e.lastName AS lastName, e.jobRole AS jobRole, "
            "e.email AS email, b.name AS branch",
            {"id": user_id},
        )
    else:
        rows = db.read(
            "MATCH (c:Customer {customerId: $id}) "
            "RETURN c.customerId AS id, c.firstName AS name, c.lastName AS lastName, c.email AS email",
            {"id": user_id},
        )
    return {"role": role, **rows[0]} if rows else None
