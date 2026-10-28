from fastapi import APIRouter, Depends, Query

from .. import auth
from ..errors import BadRequest, Forbidden
from ..schemas import PaymentCreate, ShipmentCreate
from ..services import shipments as svc

router = APIRouter(prefix="/api/shipments", tags=["Shipments"])


@router.get("", summary="List shipments (customers see only their own)")
def list_shipments(q: str | None = Query(None, max_length=80), status: str | None = None,
                   payment: str | None = Query(None, pattern="^(PAID|PARTIAL|UNPAID)$"),
                   sort: str = Query("newest", pattern="^(newest|status|amount)$"),
                   page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100),
                   customerId: int | None = Query(None, gt=0), user: dict = Depends(auth.current_user)):
    """Search by id or person name, filter by status (or ACTIVE) and payment state, sort, paginate.
    Returns items, total and counts per status."""
    if customerId is not None and user["role"] != "STAFF":
        raise Forbidden("Staff only.")
    return svc.list_shipments(user, q, status, payment, sort, page, pageSize, customerId)


@router.get("/status", tags=["Tracking"], summary="Current status board (staff)")
def status_board(user: dict = Depends(auth.staff_only)):
    """Query G3: the latest TrackingEvent (no outgoing NEXT) of every shipment."""
    return svc.status_board()


@router.get("/rates", summary="Demo rate card used for the price preview")
def rates(user: dict = Depends(auth.current_user)):
    return svc.rates()


@router.post("", status_code=201, summary="Book a shipment with one or more packages")
def book_shipment(body: ShipmentCreate, user: dict = Depends(auth.current_user)):
    """Creates shipment, packages, relationships, the first BOOKED event (and, for staff, an optional
    payment) in one transaction. Receiver is a customer id or an email."""
    data = body.model_dump()
    if (data["receiver"] is None) == (data["receiverEmail"] is None):
        raise BadRequest("Give either receiver (id) or receiverEmail.")
    if user["role"] == "CUSTOMER":
        if data["sender"] not in (None, user["id"]):
            raise Forbidden("Customers can only book shipments sent by themselves.")
        data["sender"] = user["id"]
        data["payment"] = None
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
