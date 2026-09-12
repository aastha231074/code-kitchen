"""Runs the ingest-indeed job's seed-data path end to end, once, so a fresh
docker-compose stack has jobs to match against without waiting on
Scheduler's cadence. Equivalent to `docker compose run ingest-indeed`.
"""
import sys

sys.path.insert(0, "/app")

from services.ingest_indeed.main import run

if __name__ == "__main__":
    n = run(limit=40)
    print(f"[seed-jobs] published {n} postings to jobs-raw")
