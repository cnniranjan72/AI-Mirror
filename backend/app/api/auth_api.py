"""
Auth API — register / login / me.  Additive: no existing endpoint changes.

  POST /auth/register  {username, password, email?, display_name?} -> {token, user}
  POST /auth/login     {username, password}                        -> {token, user}
  GET  /auth/me        (Authorization: Bearer <token>)             -> {user}
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.services import auth

logger = logging.getLogger(__name__)
router = APIRouter()


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


def _bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


async def current_username(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    """Optional dependency: resolve the authenticated username, or None."""
    token = _bearer(authorization)
    return auth.verify_token(token) if token else None


@router.post("/auth/register")
async def register(req: RegisterRequest):
    try:
        user = await auth.register_user(req.username, req.password, req.email, req.display_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    token = auth.create_token(user["username"])
    return {"token": token, "user": user}


@router.post("/auth/login")
async def login(req: LoginRequest):
    user = await auth.authenticate(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = auth.create_token(user["username"])
    return {"token": token, "user": user}


@router.get("/auth/me")
async def me(authorization: Optional[str] = Header(default=None)):
    username = await current_username(authorization)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await auth.get_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return {"user": user}
