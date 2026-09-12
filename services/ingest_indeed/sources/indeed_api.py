"""Real Indeed adapter -- Indeed's Publisher/Partner API is the primary,
ToS-permitted ingestion path (see ADR: legal risk lives on the LinkedIn
fallback, not here). Requires INDEED_PUBLISHER_ID / INDEED_API_KEY.

This is a thin, defensive wrapper: Indeed's actual partner API shape varies
by program tier, so treat the field mapping below as the integration point
to adjust once real credentials are issued.
"""
import requests

from services.common.config import settings


def fetch(limit: int = 25, query: str = "software engineer", location: str = "remote") -> list[dict]:
    if not settings.indeed_api_key or not settings.indeed_publisher_id:
        raise RuntimeError(
            "INDEED_API_KEY / INDEED_PUBLISHER_ID not set -- fall back to sources.seed_data.fetch() "
            "for local dev, or provision real partner credentials."
        )

    resp = requests.get(
        "https://api.indeed.com/ads/apisearch",
        params={
            "publisher": settings.indeed_publisher_id,
            "q": query,
            "l": location,
            "format": "json",
            "v": "2",
            "limit": limit,
        },
        headers={"Authorization": f"Bearer {settings.indeed_api_key}"},
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])

    return [
        {
            "external_id": r["jobkey"],
            "title": r.get("jobtitle", ""),
            "company": r.get("company", ""),
            "location": r.get("formattedLocation", ""),
            "description": r.get("snippet", ""),
            "url": r.get("url", ""),
            "posted_at": r.get("date"),
        }
        for r in results
    ]
