from fastapi import APIRouter, Depends, HTTPException, Response

from .. import auth
from ..schemas import LoginRequest
from ..services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", summary="Log in with an email only (demo)")
def login(body: LoginRequest, response: Response):
    """STAFF if the email matches an Employee node, CUSTOMER if it matches a Customer node, else 401.
    No password: this is a demo limitation."""
    user = auth_service.login(body.email)
    if not user:
        raise HTTPException(status_code=401, detail="No account with that email.")
    auth.set_session(response, user)
    return user


@router.post("/logout", summary="Log out")
def logout(response: Response):
    auth.clear_session(response)
    return {"ok": True}


@router.get("/me", summary="Who am I?")
def me(user: dict = Depends(auth.current_user)):
    return user
