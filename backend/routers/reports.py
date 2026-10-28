from fastapi import APIRouter, Depends, Query

from .. import auth
from ..services import dashboard as dash
from ..services import reports as svc

router = APIRouter(prefix="/api", tags=["Reports"])


@router.get("/dashboard", summary="Counts, status board summary, outstanding payments (staff)")
def dashboard(user: dict = Depends(auth.staff_only)):
    return dash.dashboard()


def _report(path: str, summary: str, query_id: str):
    def endpoint(user: dict = Depends(auth.staff_only)):
        return svc.run_report(path)
    endpoint.__name__ = path.replace("-", "_")
    endpoint.__doc__ = f"Query {query_id}."
    router.add_api_route(f"/reports/{path}", endpoint, methods=["GET"], summary=summary)


for _path, _summary, _qid in [
    ("busiest-locations", "Busiest locations by tracking events (staff)", "G7"),
    ("delayed", "Delayed shipments (staff)", "G9"),
    ("branch-performance", "Branch performance (staff)", "G10"),
    ("employee-activity", "Employee activity (staff)", "G11"),
    ("payments", "Payments and outstanding balance (staff)", "G12"),
    ("packages-per-shipment", "Packages per shipment (staff)", "G13"),
    ("heavier-than-average", "Shipments heavier than average (staff)", "G14"),
    ("customer-activity", "Sent / received per customer (staff)", "G15"),
    ("tracking-duration", "Hours tracked per shipment (staff)", "G16"),
]:
    _report(_path, _summary, _qid)


@router.get("/reports/customer-network", summary="Customers two hops from a customer (staff)")
def customer_network(customer_id: int = Query(1, gt=0), user: dict = Depends(auth.staff_only)):
    """Query G8."""
    return svc.customer_network(customer_id)
