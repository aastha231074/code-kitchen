"""Auth dependency shared by app-api, ai-api, and referral-api.

AUTH_MODE=dev (default locally): trusts an X-User-Email header. This is
intentionally insecure -- it exists so the whole stack runs without needing
a live Firebase project while you're building on a laptop.

AUTH_MODE=firebase (used on Cloud Run): verifies a real Firebase/Identity
Platform ID token from the Authorization header. Flip this before anything
here is exposed to the internet.
"""
from fastapi import Header, HTTPException

from .config import settings


class CurrentUser:
    def __init__(self, email: str, uid: str | None = None):
        self.email = email
        self.uid = uid or email


def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> CurrentUser:
    if settings.auth_mode == "dev":
        if not x_user_email:
            raise HTTPException(status_code=401, detail="Missing X-User-Email header (AUTH_MODE=dev)")
        return CurrentUser(email=x_user_email)

    if settings.auth_mode == "firebase":
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.removeprefix("Bearer ").strip()
        try:
            import firebase_admin
            from firebase_admin import auth as firebase_auth

            if not firebase_admin._apps:
                firebase_admin.initialize_app()
            decoded = firebase_auth.verify_id_token(token)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
        return CurrentUser(email=decoded.get("email", ""), uid=decoded.get("uid"))

    raise HTTPException(status_code=500, detail=f"Unknown AUTH_MODE '{settings.auth_mode}'")
