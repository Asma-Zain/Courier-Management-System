"""Email-only demo login, signed HttpOnly session cookie and role dependencies."""
from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer

from . import config
from .services import auth as auth_service

COOKIE_NAME = "courier_session"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(config.APP_SECRET, salt="courier-session")


def set_session(response: Response, user: dict) -> None:
    token = _serializer().dumps({"role": user["role"], "id": user["id"]})
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite="lax",
        secure=config.COOKIE_SECURE, max_age=config.SESSION_HOURS * 3600, path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in.")
    try:
        data = _serializer().loads(token, max_age=config.SESSION_HOURS * 3600)
    except BadSignature:
        raise HTTPException(status_code=401, detail="Session expired or invalid. Please log in again.")
    user = auth_service.load_user(data["role"], data["id"])
    if not user:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    return user


def staff_only(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "STAFF":
        raise HTTPException(status_code=403, detail="Staff only.")
    return user


def session(request: Request) -> dict | None:
    """Signed-cookie check without a database call (used by page routes)."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=config.SESSION_HOURS * 3600)
    except BadSignature:
        return None
    return {"role": data["role"], "id": data["id"]}
