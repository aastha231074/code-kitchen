"""Deletes referral.contacts rows past their retention window.

Run on a schedule (Cloud Scheduler -> Cloud Run Job, same pattern as
ingestion) -- e.g. daily. This is the mechanism side of ADR-04; the actual
retention period (see REFERRAL_RETENTION_DAYS / the column default in
002_referral_contacts.sql) is a legal decision, not an engineering one.
"""
import sys

sys.path.insert(0, "/app")

from services.common import db


def run() -> int:
    rows = db.fetch_all(
        "DELETE FROM referral.contacts WHERE retention_expires_at < now() RETURNING id"
    )
    print(f"[purge-referral-contacts] deleted {len(rows)} expired rows")
    return len(rows)


if __name__ == "__main__":
    run()
