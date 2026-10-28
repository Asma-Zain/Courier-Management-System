from fastapi import APIRouter, Depends

from .. import auth
from ..services import graph as svc

router = APIRouter(prefix="/api/graph", tags=["Graph"])


@router.get("/shipment/{shipment_id}", summary="Journey graph for visualisation")
def shipment_graph(shipment_id: int, user: dict = Depends(auth.current_user)):
    """G1 style: {nodes, edges} with HAS_EVENT, AT and NEXT edges."""
    return svc.shipment_graph(user, shipment_id)


@router.get("/network", summary="Hub network with km on the edges")
def network(user: dict = Depends(auth.current_user)):
    return svc.network_graph()
