"""Per-user quota enforcement for ai-api. Backed by Postgres rather than
Memorystore/Redis -- same reasoning as the dedup ADR: don't add a stateful
system when a database counter already does the job at this scale.
"""
from datetime import datetime, timezone

from fastapi import HTTPException

from .db import fetch_one


def _window_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    if period == "hour":
        return now.replace(minute=0, second=0, microsecond=0)
    if period == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    raise ValueError(period)


def check_and_increment(user_email: str, endpoint: str, limit: int, period: str) -> None:
    window = _window_start(period)
    row = fetch_one(
        """
        INSERT INTO api_quota_usage (user_email, endpoint, window_start, request_count)
        VALUES (%s, %s, %s, 1)
        ON CONFLICT (user_email, endpoint, window_start)
        DO UPDATE SET request_count = api_quota_usage.request_count + 1
        RETURNING request_count
        """,
        (user_email, endpoint, window),
    )
    if row["request_count"] > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Quota exceeded for '{endpoint}': {limit} requests per {period}. Try again later.",
        )
