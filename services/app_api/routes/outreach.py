"""The sole approval / send gate (see architecture report ADR + diagram).
Outreach rows arrive as status='pending_review' from either ai-api
(generated draft) or referral-api (contact lookup). Nothing leaves the
system until a user calls /outreach/{id}/approve here.
"""
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.app_api.config import REFERRAL_API_URL
from services.app_api.notify import send
from services.common import db
from services.common.auth import CurrentUser, get_current_user

router = APIRouter()


@router.get("/outreach")
def list_outreach(user: CurrentUser = Depends(get_current_user)):
    rows = db.fetch_all(
        """
        SELECT o.id, o.message, o.status, o.created_at, o.approved_at, o.sent_at,
               j.title, j.company
        FROM outreach o
        JOIN users u ON u.id = o.user_id
        LEFT JOIN jobs j ON j.id = o.job_id
        WHERE u.email = %s
        ORDER BY o.created_at DESC
        """,
        (user.email,),
    )
    return {"outreach": rows}


class ReferralLookupRequest(BaseModel):
    company: str
    job_id: str | None = None


@router.post("/referral/lookup")
def referral_lookup(body: ReferralLookupRequest, user: CurrentUser = Depends(get_current_user)):
    resp = requests.post(
        f"{REFERRAL_API_URL}/lookup",
        json=body.model_dump(),
        headers={"X-User-Email": user.email},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


class EditMessage(BaseModel):
    message: str


@router.put("/outreach/{outreach_id}")
def edit_outreach(outreach_id: str, body: EditMessage, user: CurrentUser = Depends(get_current_user)):
    row = _own_pending_row(outreach_id, user.email)
    db.execute("UPDATE outreach SET message = %s WHERE id = %s", (body.message, row["id"]))
    return {"id": outreach_id, "message": body.message}


@router.post("/outreach/{outreach_id}/approve")
def approve_outreach(outreach_id: str, user: CurrentUser = Depends(get_current_user)):
    row = _own_pending_row(outreach_id, user.email)

    db.execute(
        "UPDATE outreach SET status = 'approved', approved_at = now() WHERE id = %s",
        (row["id"],),
    )
    result = send(to_hint=f"contact for outreach {row['id']}", subject="Referral outreach", body=row["message"])
    if result.get("sent"):
        db.execute("UPDATE outreach SET status = 'sent', sent_at = now() WHERE id = %s", (row["id"],))

    return {"id": outreach_id, "status": "sent" if result.get("sent") else "approved"}


@router.post("/outreach/{outreach_id}/decline")
def decline_outreach(outreach_id: str, user: CurrentUser = Depends(get_current_user)):
    row = _own_pending_row(outreach_id, user.email)
    db.execute("UPDATE outreach SET status = 'declined' WHERE id = %s", (row["id"],))
    return {"id": outreach_id, "status": "declined"}


def _own_pending_row(outreach_id: str, email: str) -> dict:
    row = db.fetch_one(
        """
        SELECT o.id, o.message, o.status FROM outreach o
        JOIN users u ON u.id = o.user_id
        WHERE o.id = %s AND u.email = %s
        """,
        (outreach_id, email),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="outreach not found")
    return row
