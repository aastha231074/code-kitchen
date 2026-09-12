"""Cloud Run service: ai-api.

/match: embeds the user profile, runs a pgvector similarity query for the
top-N candidates, then sends only that shortlist to Gemini Flash for a
rerank + one-line explanation. This ordering -- cheap vector math first,
expensive model call only on the shortlist -- is the single biggest cost
lever in the whole system (see ADR-02).

/generate: Gemini Pro produces the tailored resume + outreach draft for one
specific job the user picked. Both endpoints are quota-gated per user so
cost/abuse can't scale unbounded with active sessions (Fool finding #6).

pgvector migration trigger (monitored, not indefinite): if `jobs` exceeds
~5M rows or p95 similarity-query latency exceeds ~300ms, move to Vertex AI
Vector Search instead of scaling this instance further. See
services/common/config.py: pgvector_row_ceiling / pgvector_latency_ceiling_ms.
"""
import time

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from services.common import db
from services.common.ai import embed_text, generate_resume_and_outreach, rerank_and_explain
from services.common.auth import CurrentUser, get_current_user
from services.common.config import settings
from services.common.quota import check_and_increment

app = FastAPI(title="ai-api")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


class MatchRequest(BaseModel):
    top_n: int = 20


@app.post("/match")
def match(req: MatchRequest, user: CurrentUser = Depends(get_current_user)):
    check_and_increment(user.email, "match", settings.match_requests_per_hour, "hour")

    user_row = _get_or_create_user(user.email)
    profile = user_row["profile"]
    profile_text = _profile_to_text(profile)
    profile_vec = embed_text(profile_text)

    start = time.time()
    candidates = db.fetch_all(
        """
        SELECT id, title, company, location, description,
               1 - (embedding <=> %s::vector) AS similarity
        FROM jobs
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (db.to_vector_literal(profile_vec), db.to_vector_literal(profile_vec), req.top_n),
    )
    latency_ms = (time.time() - start) * 1000
    if latency_ms > settings.pgvector_latency_ceiling_ms:
        print(
            f"[ai-api] WARNING pgvector query took {latency_ms:.0f}ms, over the "
            f"{settings.pgvector_latency_ceiling_ms}ms migration-trigger threshold (ADR-02)"
        )

    results = []
    for job in candidates:
        rationale = rerank_and_explain(profile, dict(job))
        db.execute(
            """
            INSERT INTO matches (user_id, job_id, similarity, rationale)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, job_id) DO UPDATE SET
                similarity = EXCLUDED.similarity, rationale = EXCLUDED.rationale, created_at = now()
            """,
            (user_row["id"], job["id"], job["similarity"], rationale),
        )
        results.append(
            {
                "job_id": str(job["id"]),
                "title": job["title"],
                "company": job["company"],
                "location": job["location"],
                "similarity": job["similarity"],
                "rationale": rationale,
            }
        )

    return {"matches": results, "query_latency_ms": round(latency_ms, 1)}


class GenerateRequest(BaseModel):
    job_id: str


@app.post("/generate")
def generate(req: GenerateRequest, user: CurrentUser = Depends(get_current_user)):
    check_and_increment(user.email, "generate", settings.generate_requests_per_day, "day")

    user_row = _get_or_create_user(user.email)
    job = db.fetch_one("SELECT * FROM jobs WHERE id = %s", (req.job_id,))
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    output = generate_resume_and_outreach(user_row["profile"], dict(job))

    application = db.fetch_one(
        """
        INSERT INTO applications (user_id, job_id, resume_text, status)
        VALUES (%s, %s, %s, 'draft')
        RETURNING id
        """,
        (user_row["id"], job["id"], output["resume"]),
    )
    outreach = db.fetch_one(
        """
        INSERT INTO outreach (user_id, job_id, message, status)
        VALUES (%s, %s, %s, 'pending_review')
        RETURNING id
        """,
        (user_row["id"], job["id"], output["outreach"]),
    )

    return {
        "application_id": str(application["id"]),
        "outreach_id": str(outreach["id"]),
        "resume": output["resume"],
        "outreach_message": output["outreach"],
    }


def _get_or_create_user(email: str) -> dict:
    row = db.fetch_one("SELECT * FROM users WHERE email = %s", (email,))
    if row:
        return row
    return db.fetch_one(
        "INSERT INTO users (email, profile) VALUES (%s, %s) RETURNING *",
        (email, "{}"),
    )


def _profile_to_text(profile: dict) -> str:
    skills = ", ".join(profile.get("skills", []))
    return (
        f"Skills: {skills}. Experience: {profile.get('experience', '')}. "
        f"Preferences: {profile.get('preferences', '')}. Location: {profile.get('location', '')}"
    )
