"""CRUD + the application half of the approval gate: a generated resume
sits in status='draft' until the user explicitly marks it applied. Nothing
auto-submits anything to an employer.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.common import db
from services.common.auth import CurrentUser, get_current_user

router = APIRouter()


@router.get("/applications")
def list_applications(user: CurrentUser = Depends(get_current_user)):
    rows = db.fetch_all(
        """
        SELECT a.id, a.status, a.applied_at, a.created_at, a.resume_text,
               j.title, j.company, j.location
        FROM applications a
        JOIN jobs j ON j.id = a.job_id
        JOIN users u ON u.id = a.user_id
        WHERE u.email = %s
        ORDER BY a.created_at DESC
        """,
        (user.email,),
    )
    return {"applications": rows}


class StatusUpdate(BaseModel):
    status: str  # 'applied' | 'responded' | 'rejected' | 'offer'


@router.post("/applications/{application_id}/status")
def update_status(application_id: str, body: StatusUpdate, user: CurrentUser = Depends(get_current_user)):
    allowed = {"applied", "responded", "rejected", "offer"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {allowed}")

    row = db.fetch_one(
        """
        UPDATE applications a SET status = %s, updated_at = now(),
               applied_at = CASE WHEN %s = 'applied' THEN now() ELSE a.applied_at END
        FROM users u
        WHERE a.id = %s AND a.user_id = u.id AND u.email = %s
        RETURNING a.id, a.status
        """,
        (body.status, body.status, application_id, user.email),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="application not found")
    return row
