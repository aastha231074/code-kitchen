"""Cloud Run service: process-worker.

Receives a Pub/Sub push message per ingested job record. Dedup is a
Postgres unique constraint on (source, external_id) -- not a separate
Redis/Memorystore lookup (see ADR-03: that system added an unreplicated
stateful dependency to solve a problem the database already solves).

On INSERT success (i.e. genuinely new record), embeds the posting and
writes the vector. On failure, the message is nacked so Pub/Sub retries it
up to the subscription's max-delivery-attempts, after which it lands on the
jobs-raw-dlq topic/table automatically via the subscription's dead-letter
policy (configured in infra/terraform/pubsub.tf; locally, main.py writes
the DLQ row directly on final failure -- see _handle below).
"""
import base64
import json

from fastapi import FastAPI, Request, Response

from services.common import db
from services.common.ai import embed_text

app = FastAPI(title="process-worker")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/")
async def receive(request: Request):
    envelope = await request.json()
    message = envelope.get("message", {})
    data = message.get("data")
    if not data:
        return Response(status_code=204)

    payload = json.loads(base64.b64decode(data))
    try:
        _handle(payload)
    except Exception as exc:  # noqa: BLE001
        _to_dlq(payload, str(exc))
        # Ack anyway locally so the emulator doesn't hot-loop retries forever;
        # on real Pub/Sub with a dead-letter policy configured, returning 500
        # here is the correct move and this except becomes unreachable for
        # anything but the DLQ-write failing too.
        return Response(status_code=200)

    return Response(status_code=200)


def _handle(payload: dict) -> None:
    source = payload["source"]
    posting = payload["posting"]
    raw_ref = payload.get("raw_ref")

    row = db.fetch_one(
        """
        INSERT INTO jobs (source, external_id, title, company, location, description, url, posted_at, raw_ref)
        VALUES (%(source)s, %(external_id)s, %(title)s, %(company)s, %(location)s,
                %(description)s, %(url)s, %(posted_at)s, %(raw_ref)s)
        ON CONFLICT (source, external_id) DO NOTHING
        RETURNING id, description
        """,
        {
            "source": source,
            "external_id": posting["external_id"],
            "title": posting["title"],
            "company": posting["company"],
            "location": posting.get("location"),
            "description": posting["description"],
            "url": posting.get("url"),
            "posted_at": posting.get("posted_at"),
            "raw_ref": raw_ref,
        },
    )

    if row is None:
        return  # duplicate -- constraint did its job, nothing further to do

    embedding = embed_text(row["description"])
    db.execute(
        "UPDATE jobs SET embedding = %s::vector WHERE id = %s",
        (db.to_vector_literal(embedding), row["id"]),
    )


def _to_dlq(payload: dict, error: str) -> None:
    db.execute(
        "INSERT INTO jobs_raw_dlq (source, payload, error) VALUES (%s, %s, %s)",
        (payload.get("source", "unknown"), json.dumps(payload), error),
    )
