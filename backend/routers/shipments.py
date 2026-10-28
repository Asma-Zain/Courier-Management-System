from fastapi import APIRouter, Depends

from .. import auth
from ..errors import BadRequest, Forbidden
from ..schemas import PaymentCreate, ShipmentCreate
from ..services import shipments as svc

router = APIRouter(prefix="/api/shipments", tags=["Shipments"])


@router.get("", summary="List shipments (customers see only their own)")
def list_shipments(user: dict = Depends(auth.current_user)):
    return svc.list_shipments(user)


# declared before /{shipment_id} so "status" is not parsed as an id
@router.get("/status", tags=["Tracking"], summary="Current status board (staff)")
def status_board(user: dict = Depends(auth.staff_only)):
    """Query G3: the latest TrackingEvent (no outgoing NEXT) of every shipment."""
    return svc.status_board()


@router.post("", status_code=201, summary="Book a shipment with one or more packages")
def book_shipment(body: ShipmentCreate, user: dict = Depends(auth.current_user)):
    """Creates shipment, packages, relationships and the first BOOKED event in one transaction."""
    data = body.model_dump()
    if user["role"] == "CUSTOMER":
        if data["sender"] not in (None, user["id"]):
            raise Forbidden("Customers can only book shipments sent by themselves.")
        data["sender"] = user["id"]
    elif data["sender"] is None:
        raise BadRequest("sender is required when staff book a shipment.")
    return svc.book_shipment(user, data)


@router.get("/{shipment_id}", summary="Shipment details")
def get_shipment(shipment_id: int, user: dict = Depends(auth.current_user)):
    """Query G2: sender, receiver, packages, payment and current status."""
    return svc.get_shipment(user, shipment_id)


@router.post("/{shipment_id}/payment", status_code=201, tags=["Payments"], summary="Record a payment (staff)")
def record_payment(shipment_id: int, body: PaymentCreate, user: dict = Depends(auth.staff_only)):
    return svc.record_payment(shipment_id, body.model_dump())
