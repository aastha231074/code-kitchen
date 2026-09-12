"""Cloud Run service: referral-api.

Finds public professional contacts at a target company and drafts an
outreach message for the user to review. This touches personal data about
people who never signed up for Code Kitchen -- that's a materially
different privacy obligation than the user's own account data, which is
why it's isolated:

  - its own schema (referral.*, not public.*)
  - its own retention TTL (see db/migrations/002_referral_contacts.sql --
    purge job in scripts/purge_referral_contacts.py)
  - its own service, so IAM can grant contact-data access only here and to
    app-api, not to ai-api or process-worker

The actual lookup below is a mock: a real implementation needs its own
scoped, rate-limited, ToS-compliant source, and the retention period is a
placeholder pending legal sign-off (see architecture report, section 7).
Nothing here ever sends anything -- every row is written pending_review and
only app-api's approval gate can move it forward.
"""
import random

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from services.common import db
from services.common.auth import CurrentUser, get_current_user

app = FastAPI(title="referral-api")

_MOCK_TITLES = ["Engineering Manager", "Senior Recruiter", "Staff Engineer", "VP Engineering"]
_MOCK_FIRST = ["Alex", "Jordan", "Sam", "Taylor", "Morgan", "Casey"]
_MOCK_LAST = ["Chen", "Patel", "Garcia", "Nguyen", "Okafor", "Kowalski"]


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


class LookupRequest(BaseModel):
    company: str
    job_id: str | None = None


@app.post("/lookup")
def lookup(req: LookupRequest, user: CurrentUser = Depends(get_current_user)):
    rng = random.Random(req.company)  # deterministic per company for demo purposes
    name = f"{rng.choice(_MOCK_FIRST)} {rng.choice(_MOCK_LAST)}"
    title = rng.choice(_MOCK_TITLES)

    contact = db.fetch_one(
        """
        INSERT INTO referral.contacts (company, contact_name, contact_title, source_url)
        VALUES (%s, %s, %s, %s)
        RETURNING id, retention_expires_at
        """,
        (req.company, name, title, "https://example.invalid/mock-public-profile"),
    )

    user_row = db.fetch_one("SELECT id FROM users WHERE email = %s", (user.email,))
    message = (
        f"Hi {name.split()[0]}, I noticed you're a {title} at {req.company}. "
        f"I'm applying there and would appreciate hearing about your experience -- "
        f"open to a quick chat?"
    )
    outreach = db.fetch_one(
        """
        INSERT INTO outreach (user_id, job_id, contact_id, message, status)
        VALUES (%s, %s, %s, %s, 'pending_review')
        RETURNING id
        """,
        (user_row["id"], req.job_id, contact["id"], message),
    )

    return {
        "contact_id": str(contact["id"]),
        "outreach_id": str(outreach["id"]),
        "contact_name": name,
        "contact_title": title,
        "message": message,
        "status": "pending_review",
        "retention_expires_at": contact["retention_expires_at"].isoformat(),
    }
