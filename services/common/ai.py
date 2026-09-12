"""Gemini + embedding calls, with a deterministic offline mock so the whole
stack runs on a laptop with no API key. Set GEMINI_API_KEY (and unset
USE_MOCK_AI) to hit the real models.

Model tiering matches ADR: Flash for cheap bulk ranking, Pro (+ cached
context) only for the final user-facing resume/outreach draft.
"""
import hashlib
import json
import struct

from .config import settings

_genai_client = None


def _client():
    global _genai_client
    if _genai_client is None:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        _genai_client = genai
    return _genai_client


def embed_text(text: str) -> list[float]:
    """Returns a vector of settings.embedding_dim floats."""
    if settings.use_mock_ai:
        return _mock_embedding(text, settings.embedding_dim)

    genai = _client()
    result = genai.embed_content(model=f"models/{settings.embedding_model}", content=text)
    return result["embedding"]


def _mock_embedding(text: str, dim: int) -> list[float]:
    """Deterministic, content-sensitive pseudo-embedding for offline dev.
    Not semantically meaningful beyond exact/near-duplicate text matching --
    good enough to exercise the matching pipeline without network calls.
    """
    vec = []
    h = text.encode("utf-8")
    counter = 0
    while len(vec) < dim:
        digest = hashlib.sha256(h + counter.to_bytes(4, "big")).digest()
        for i in range(0, len(digest), 4):
            if len(vec) >= dim:
                break
            (n,) = struct.unpack("I", digest[i : i + 4])
            vec.append((n / 2**32) * 2 - 1)  # [-1, 1]
        counter += 1
    return vec


def rerank_and_explain(user_profile: dict, job: dict) -> str:
    """Gemini Flash: short explanation of why a shortlisted job fits."""
    if settings.use_mock_ai:
        skills = ", ".join(user_profile.get("skills", [])[:3]) or "your background"
        return f"Matches on {skills}; role '{job['title']}' at {job['company']} overlaps your stated preferences."

    genai = _client()
    model = genai.GenerativeModel(settings.gemini_flash_model)
    prompt = (
        "In one sentence, explain why this job fits this candidate. "
        f"Candidate profile: {json.dumps(user_profile)}. "
        f"Job: {job['title']} at {job['company']}. {job['description'][:800]}"
    )
    resp = model.generate_content(prompt)
    return resp.text.strip()


def generate_resume_and_outreach(user_profile: dict, job: dict) -> dict:
    """Gemini Pro: tailored resume + outreach draft. Context (job description)
    is reused across users, so a real deployment should wrap this call with
    Gemini context caching keyed on job_id -- left as a TODO marker since the
    caching API needs a live project to demo meaningfully.
    """
    if settings.use_mock_ai:
        resume = (
            f"{user_profile.get('name', 'Candidate')}\n"
            f"Target role: {job['title']} at {job['company']}\n\n"
            f"Summary: Experienced professional with skills in "
            f"{', '.join(user_profile.get('skills', []))}, aligned to this role's requirements.\n"
        )
        outreach = (
            f"Hi -- I'm applying for the {job['title']} role at {job['company']} and would love "
            f"to hear about your experience on the team. Open to a quick chat?"
        )
        return {"resume": resume, "outreach": outreach}

    genai = _client()
    model = genai.GenerativeModel(settings.gemini_pro_model)
    prompt = (
        "Write a tailored one-page resume summary and a short referral outreach message. "
        f"Candidate profile: {json.dumps(user_profile)}. "
        f"Job: {job['title']} at {job['company']}. {job['description'][:2000]}. "
        'Respond as JSON: {"resume": "...", "outreach": "..."}'
    )
    resp = model.generate_content(prompt)
    try:
        return json.loads(resp.text)
    except json.JSONDecodeError:
        return {"resume": resp.text, "outreach": ""}
