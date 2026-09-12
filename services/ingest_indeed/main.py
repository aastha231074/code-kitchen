"""Cloud Run Job: ingest-indeed.

Runs once per invocation (triggered by Cloud Scheduler -> Pub/Sub locally,
or a direct `gcloud run jobs execute` / cron in prod), fetches a batch of
postings, lands the raw payload in storage, and publishes one pointer
message per record to jobs-raw for process-worker to pick up.

Official API is primary. There is deliberately no scrape fallback wired in
here -- LinkedIn's ToS-risk fallback lives in services/ingest_linkedin as a
separate, explicitly gated job (see ADR-01 and the architecture report's
callout on what engineering can't resolve on its own).
"""
import json
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, "/app")  # see Dockerfile: repo root is copied to /app

from services.common import db, storage
from services.common.config import settings
from services.common.pubsub import ensure_topic, publish
from services.ingest_indeed.sources import indeed_api, seed_data

SOURCE = "indeed"


def _record_heartbeat(count: int) -> None:
    db.execute(
        """
        INSERT INTO ingestion_heartbeats (source, last_success_at, last_record_count, consecutive_empty_runs)
        VALUES (%s, now(), %s, %s)
        ON CONFLICT (source) DO UPDATE SET
            last_success_at = now(),
            last_record_count = EXCLUDED.last_record_count,
            consecutive_empty_runs = CASE WHEN EXCLUDED.last_record_count = 0
                THEN ingestion_heartbeats.consecutive_empty_runs + 1 ELSE 0 END
        """,
        (SOURCE, count, 0 if count else 1),
    )


def run(limit: int = 25) -> int:
    ensure_topic(settings.topic_jobs_raw)

    if settings.indeed_api_key and settings.indeed_publisher_id:
        postings = indeed_api.fetch(limit=limit)
    else:
        print("[ingest-indeed] no API credentials set, using seed data for local/demo run")
        postings = seed_data.fetch(limit=limit)

    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    published = 0
    for posting in postings:
        raw_path = f"raw-jobs/{SOURCE}/{date_prefix}/{posting['external_id']}.json"
        raw_ref = storage.write_bytes(raw_path, json.dumps(posting).encode("utf-8"))

        publish(
            settings.topic_jobs_raw,
            {"source": SOURCE, "raw_ref": raw_ref, "posting": posting},
        )
        published += 1

    _record_heartbeat(published)
    print(f"[ingest-indeed] published {published} records")
    return published


if __name__ == "__main__":
    start = time.time()
    n = run()
    print(f"[ingest-indeed] done in {time.time() - start:.1f}s, {n} records")
