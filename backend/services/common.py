"""Shared Cypher fragments and the shipment access check."""
from .. import db
from ..errors import Forbidden, NotFound

# Staff see everything; customers only shipments they sent or are addressed to.
# Needs $role and $cid parameters and a bound variable `s`.
ACCESS = """(
    $role = 'STAFF'
    OR EXISTS { MATCH (:Customer {customerId: $cid})-[:SENT]->(s) }
    OR EXISTS { MATCH (s)-[:ADDRESSED_TO]->(:Customer {customerId: $cid}) }
)"""


def access_params(user: dict) -> dict:
    return {"role": user["role"], "cid": user["id"] if user["role"] == "CUSTOMER" else -1}


def require_shipment_access(user: dict, shipment_id: int) -> None:
    """404 if the shipment does not exist, 403 if the user may not see it."""
    rows = db.read(
        f"MATCH (s:Shipment {{shipmentId: $sid}}) RETURN {ACCESS} AS allowed",
        {"sid": shipment_id, **access_params(user)},
    )
    if not rows:
        raise NotFound(f"Shipment {shipment_id} not found.")
    if not rows[0]["allowed"]:
        raise Forbidden("You do not have access to this shipment.")
