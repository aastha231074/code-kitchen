from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.common import db
from services.common.auth import CurrentUser, get_current_user

router = APIRouter()


class ProfileUpdate(BaseModel):
    skills: list[str] = []
    experience: str = ""
    preferences: str = ""
    location: str = ""


@router.get("/profile")
def get_profile(user: CurrentUser = Depends(get_current_user)):
    row = _get_or_create_user(user.email)
    return {"email": row["email"], "profile": row["profile"]}


@router.put("/profile")
def update_profile(body: ProfileUpdate, user: CurrentUser = Depends(get_current_user)):
    row = db.fetch_one(
        """
        UPDATE users SET profile = %s WHERE email = %s
        RETURNING email, profile
        """,
        (body.model_dump_json(), user.email),
    )
    if row is None:
        row = _get_or_create_user(user.email, profile=body.model_dump())
    return {"email": row["email"], "profile": row["profile"]}


def _get_or_create_user(email: str, profile: dict | None = None) -> dict:
    row = db.fetch_one("SELECT * FROM users WHERE email = %s", (email,))
    if row:
        return row
    import json

    return db.fetch_one(
        "INSERT INTO users (email, profile) VALUES (%s, %s) RETURNING *",
        (email, json.dumps(profile or {})),
    )
