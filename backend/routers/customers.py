from fastapi import APIRouter, Depends, Query, Request

from .. import auth, ratelimit
from ..errors import Forbidden
from ..schemas import CustomerCreate, CustomerUpdate
from ..services import branches as branch_service
from ..services import customers as svc

router = APIRouter(prefix="/api", tags=["Customers"])


def _own_or_staff(user: dict, customer_id: int) -> None:
    if user["role"] != "STAFF" and user["id"] != customer_id:
        raise Forbidden("You can only access your own profile.")


@router.get("/customers", summary="List customers (staff)")
def list_customers(user: dict = Depends(auth.staff_only)):
    return svc.list_customers()


@router.post("/customers", status_code=201, summary="Create a customer (staff)")
def create_customer(body: CustomerCreate, user: dict = Depends(auth.staff_only)):
    """Duplicate customerId or email returns 409 (uniqueness constraint, demo C7)."""
    return svc.create_customer(body.model_dump())


@router.get("/customers/lookup", summary="Find a customer id by email (any logged-in user)")
def lookup(request: Request, email: str = Query(..., max_length=120), user: dict = Depends(auth.current_user)):
    """Customers get {exists, displayName} only; staff also get id, name and city. Rate limited."""
    ratelimit.check(f"lookup:user:{user['role']}{user['id']}", 30)
    ratelimit.check(f"lookup:ip:{request.client.host if request.client else '-'}", 60)
    return svc.lookup_by_email(user, email)


@router.get("/customers/{customer_id}", summary="Get a customer (staff, or the customer themself)")
def get_customer(customer_id: int, user: dict = Depends(auth.current_user)):
    _own_or_staff(user, customer_id)
    return svc.get_customer(customer_id)


@router.patch("/customers/{customer_id}", summary="Update phone / address")
def update_customer(customer_id: int, body: CustomerUpdate, user: dict = Depends(auth.current_user)):
    _own_or_staff(user, customer_id)
    return svc.update_customer(customer_id, body.model_dump(exclude_none=True))


@router.delete("/customers/{customer_id}", status_code=204, summary="Delete a customer (staff)")
def delete_customer(customer_id: int, user: dict = Depends(auth.staff_only)):
    """409 if the customer has sent or received any shipment."""
    svc.delete_customer(customer_id)


@router.get("/branches", tags=["Routes"], summary="List branches and hubs")
def list_branches(user: dict = Depends(auth.current_user)):
    return branch_service.list_branches()
