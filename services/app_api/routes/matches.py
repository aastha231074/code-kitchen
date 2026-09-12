"""Fans out to ai-api. app-api never talks to Cloud SQL's `jobs`/`matches`
tables for this path -- ai-api owns matching end to end; app-api is purely
the BFF that forwards the authenticated request.
"""
import requests
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.app_api.config import AI_API_URL
from services.common.auth import CurrentUser, get_current_user

router = APIRouter()


class MatchRequest(BaseModel):
    top_n: int = 20


@router.post("/match")
def match(body: MatchRequest, user: CurrentUser = Depends(get_current_user)):
    resp = requests.post(
        f"{AI_API_URL}/match",
        json=body.model_dump(),
        headers={"X-User-Email": user.email},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


class GenerateRequest(BaseModel):
    job_id: str


@router.post("/generate")
def generate(body: GenerateRequest, user: CurrentUser = Depends(get_current_user)):
    resp = requests.post(
        f"{AI_API_URL}/generate",
        json=body.model_dump(),
        headers={"X-User-Email": user.email},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()
