from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.services.demo_users import authenticate_demo_user, get_demo_user, list_demo_users


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.get("/users")
def get_users():
    return list_demo_users()


@router.post("/login")
def login(request: LoginRequest):
    user = authenticate_demo_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return user


@router.get("/me")
def me(x_demo_user: Optional[str] = Header(default=None)):
    user = get_demo_user(x_demo_user)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    return user
