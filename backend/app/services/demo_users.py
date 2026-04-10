from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DemoUser:
    username: str
    display_name: str
    password: str


DEMO_USERS = [
    DemoUser(username="alejandro.barrera", display_name="Alejandro Barrera", password="123456"),
    DemoUser(username="victoria.corroto", display_name="Victoria Corroto", password="123456"),
    DemoUser(username="marta.sanz", display_name="Marta Sanz", password="123456"),
    DemoUser(username="carlo.villegas", display_name="Carlo Villegas", password="123456"),
]


def list_demo_users() -> list[dict[str, str]]:
    return [
        {
            "username": user.username,
            "display_name": user.display_name,
        }
        for user in DEMO_USERS
    ]


def get_demo_user(username: Optional[str]) -> Optional[dict[str, str]]:
    if not username or not isinstance(username, str):
        return None
    lowered = username.strip().lower()
    for user in DEMO_USERS:
        if user.username == lowered:
            return {"username": user.username, "display_name": user.display_name}
    return None


def authenticate_demo_user(username: str, password: str) -> Optional[dict[str, str]]:
    lowered = (username or "").strip().lower()
    for user in DEMO_USERS:
        if user.username == lowered and user.password == password:
            return {"username": user.username, "display_name": user.display_name}
    return None
