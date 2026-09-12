"""Cloud Run Job: ingest-linkedin -- explicitly gated fallback, not a
default ingestion path.

LinkedIn's Terms of Service prohibit scraping, and platforms have won
contract-based claims against scrapers even where anti-hacking statutes
didn't apply (see architecture report, section 7). Whether to run this job
at all is a legal/business risk decision, not an engineering one -- this
file enforces that by refusing to run unless ENABLE_LINKEDIN_SCRAPE=true is
set explicitly at deploy time, and by writing every run to a visible flag
in the heartbeat table so it's never silently on.

No actual scraping logic is implemented here. Wire in a real scraper only
after that legal sign-off exists.
"""
import sys

sys.path.insert(0, "/app")

from services.common import db
from services.common.config import settings

SOURCE = "linkedin"


def run() -> int:
    if not settings.enable_linkedin_scrape:
        print(
            "[ingest-linkedin] disabled. This ingestion path is a ToS-risk fallback and requires "
            "ENABLE_LINKEDIN_SCRAPE=true plus an explicit legal risk-acceptance sign-off before it "
            "runs. See architecture report, section 7."
        )
        db.execute(
            """
            INSERT INTO ingestion_heartbeats (source, last_success_at, last_record_count, consecutive_empty_runs)
            VALUES (%s, NULL, 0, 0)
            ON CONFLICT (source) DO NOTHING
            """,
            (SOURCE,),
        )
        return 0

    raise NotImplementedError(
        "ENABLE_LINKEDIN_SCRAPE=true is set, but no scraper is wired in. Implement one only after "
        "legal sign-off on ToS/retention/lawful-basis questions -- this is intentionally left blank."
    )


if __name__ == "__main__":
    n = run()
    print(f"[ingest-linkedin] done, {n} records")
