import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from .. import auth, config, ratelimit
from ..schemas import LoginRequest
from ..services import auth as auth_service

log = logging.getLogger("courier.auth")
router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", summary="Log in with an email only (demo)")
def login(request: Request, body: LoginRequest, response: Response):
    """STAFF if the email matches an Employee node, CUSTOMER if it matches a Customer node, else 401.
    No password: this is a demo limitation."""
    ratelimit.check(f"login:{request.client.host if request.client else '-'}", 10)
    user = auth_service.login(body.email)
    if not user:
        log.warning("failed login from %s", request.client.host if request.client else "-")
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


@router.get("/config", summary="Public UI settings")
def public_config():
    return {"env": config.APP_ENV, "demoLogins": config.SHOW_DEMO_LOGINS, "docs": config.ENABLE_DOCS}
