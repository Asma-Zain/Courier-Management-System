from fastapi import APIRouter, Depends

from .. import auth
from ..schemas import EventCreate
from ..services import tracking as svc

router = APIRouter(prefix="/api/shipments", tags=["Tracking"])


@router.get("/{shipment_id}/track", summary="Ordered journey of a shipment")
def track(shipment_id: int, user: dict = Depends(auth.current_user)):
    """Query C3. Customers get 403 for shipments they neither sent nor receive."""
    return svc.track(user, shipment_id)


@router.post("/{shipment_id}/events", status_code=201, summary="Append a tracking event (staff)")
def add_event(shipment_id: int, body: EventCreate, user: dict = Depends(auth.staff_only)):
    """Query C4: creates HAS_EVENT, NEXT, AT and LOGGED in one transaction."""
    return svc.add_event(user, shipment_id, body.status, body.branch)
