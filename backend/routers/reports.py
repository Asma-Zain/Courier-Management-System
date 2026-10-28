from fastapi import APIRouter, Depends, Query

from .. import auth
from ..services import overview as ov
from ..services import reports as svc

router = APIRouter(prefix="/api", tags=["Reports"])


@router.get("/overview", summary="Staff overview: KPIs, attention list, activity, hubs (staff)")
def overview(user: dict = Depends(auth.staff_only)):
    return ov.overview()


@router.get("/reports", summary="Report catalogue with titles, columns and Cypher text (staff)")
def catalogue(user: dict = Depends(auth.staff_only)):
    return svc.metadata()


@router.get("/reports/{slug}", summary="Run a report (staff)")
def run_report(slug: str, customer_id: int | None = Query(None, gt=0), user: dict = Depends(auth.staff_only)):
    """Query ids G7 to G16 (see the catalogue). Returns the report metadata and its rows."""
    return svc.run_report(slug, customer_id)
