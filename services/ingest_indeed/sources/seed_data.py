"""Seed/mock job postings used when INDEED_API_KEY isn't set (local dev,
demos, or the lab's temporary sandbox before real API credentials exist).
Structurally identical to what the real API adapter returns.
"""
import random

_TITLES = [
    "Backend Engineer", "Frontend Engineer", "Data Scientist", "Product Manager",
    "DevOps Engineer", "Machine Learning Engineer", "Site Reliability Engineer",
    "Full Stack Engineer", "Data Engineer", "Engineering Manager",
]
_COMPANIES = [
    "Northwind Systems", "Bluepeak Analytics", "Fernbridge Labs", "Cascade Robotics",
    "Ironvale Software", "Meridian Health Tech", "Solstice Cloud", "Harborlight Fintech",
]
_LOCATIONS = ["Remote", "New York, NY", "San Francisco, CA", "Austin, TX", "Seattle, WA"]

_SKILL_POOL = [
    "Python", "TypeScript", "React", "Kubernetes", "PostgreSQL", "AWS", "GCP",
    "Terraform", "Go", "Machine Learning", "SQL", "Docker", "CI/CD", "Node.js",
]


def fetch(limit: int = 25, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    postings = []
    for i in range(limit):
        title = rng.choice(_TITLES)
        company = rng.choice(_COMPANIES)
        skills = rng.sample(_SKILL_POOL, k=rng.randint(3, 6))
        postings.append(
            {
                "external_id": f"seed-{i:04d}-{rng.randint(1000,9999)}",
                "title": title,
                "company": company,
                "location": rng.choice(_LOCATIONS),
                "description": (
                    f"{company} is hiring a {title}. We're looking for someone with experience in "
                    f"{', '.join(skills)}. You'll work on production systems end to end."
                ),
                "url": f"https://example.invalid/jobs/seed-{i:04d}",
                "posted_at": None,
            }
        )
    return postings
