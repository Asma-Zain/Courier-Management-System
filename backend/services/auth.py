from .. import db


def login(email: str) -> dict | None:
    email = email.strip().lower()
    staff = db.read(
        "MATCH (e:Employee {email: $email}) "
        "RETURN e.employeeId AS id, e.firstName AS name, e.jobRole AS jobRole, e.email AS email",
        {"email": email},
    )
    if staff:
        return {"role": "STAFF", **staff[0]}
    cust = db.read(
        "MATCH (c:Customer {email: $email}) "
        "RETURN c.customerId AS id, c.firstName AS name, c.email AS email",
        {"email": email},
    )
    if cust:
        return {"role": "CUSTOMER", **cust[0]}
    return None


def load_user(role: str, user_id: int) -> dict | None:
    if role == "STAFF":
        rows = db.read(
            "MATCH (e:Employee {employeeId: $id}) "
            "RETURN e.employeeId AS id, e.firstName AS name, e.jobRole AS jobRole, e.email AS email",
            {"id": user_id},
        )
    else:
        rows = db.read(
            "MATCH (c:Customer {customerId: $id}) "
            "RETURN c.customerId AS id, c.firstName AS name, c.email AS email",
            {"id": user_id},
        )
    return {"role": role, **rows[0]} if rows else None
