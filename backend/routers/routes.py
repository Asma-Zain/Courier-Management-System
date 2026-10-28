from fastapi import APIRouter, Depends, Query

from .. import auth
from ..services import routes as svc

router = APIRouter(prefix="/api", tags=["Routes"])


@router.get("/routes/fewest-hops", summary="Route with the fewest hops")
def fewest_hops(from_: str = Query(..., alias="from", examples=["Hyderabad Hub"]),
                to: str = Query(..., examples=["Coimbatore Hub"]),
                user: dict = Depends(auth.current_user)):
    """Query G4 (shortestPath)."""
    return svc.fewest_hops(from_, to)


@router.get("/routes/fewest-km", summary="Top 3 routes by kilometres")
def fewest_km(from_: str = Query(..., alias="from", examples=["Hyderabad Hub"]),
              to: str = Query(..., examples=["Coimbatore Hub"]),
              user: dict = Depends(auth.current_user)):
    """Query G5 (variable-length path + reduce)."""
    return svc.fewest_km(from_, to)


@router.get("/hubs/{name}/impact", summary="Who is waiting on this hub? (staff)")
def hub_impact(name: str, user: dict = Depends(auth.staff_only)):
    """Query G6."""
    return svc.hub_impact(name)
