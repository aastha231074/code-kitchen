"""Cloud Run service: app-api (BFF).

Single entry point for the web UI. Fans out to ai-api and referral-api,
owns CRUD on applications/outreach, and is the only place in the system
that flips a row to 'approved'/'sent' -- see routes/outreach.py.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.app_api.routes import applications, matches, outreach, profile

app = FastAPI(title="app-api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the real web origin before anything but local dev
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


app.include_router(profile.router)
app.include_router(matches.router)
app.include_router(applications.router)
app.include_router(outreach.router)
