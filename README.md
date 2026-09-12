# Code Kitchen

An AI job application tracker: ingest public job postings, match them
against a user's profile, draft a tailored resume and referral outreach
message with Gemini, and track applications end to end -- with the user
approving every outbound action.

This repo implements the **v3 architecture** from the project's
architecture review (Cloud Architect -> Architecture Designer -> The Fool
-> Architecture Designer cycle): scheduled ingestion via Cloud Run Jobs,
Pub/Sub buffering with a dead-letter queue, dedup via a Postgres unique
constraint (no Redis), a pgvector pre-filter before any Gemini call,
model-tiered generation (Flash for ranking, Pro for final output),
isolated storage for third-party referral-contact PII with its own
retention job, and per-user quotas on every AI-facing endpoint.

## Repo layout

```
services/
  common/           shared config, db, pubsub, auth, ai, storage, quota helpers
  ingest_indeed/     Cloud Run Job -- official API (primary), seed data fallback for local dev
  ingest_linkedin/   Cloud Run Job -- ToS-risk scrape fallback, disabled unless explicitly enabled
  process_worker/    Cloud Run service -- Pub/Sub push subscriber: dedup + embed
  ai_api/            Cloud Run service -- /match (pgvector + Gemini Flash), /generate (Gemini Pro)
  referral_api/      Cloud Run service -- mocked contact lookup, isolated PII schema
  app_api/           Cloud Run service -- BFF: auth, CRUD, the sole approval/send gate
web/                 Static HTML/JS frontend (no build step)
db/migrations/       Postgres schema (pgvector, dedup constraint, referral schema, quota table)
infra/terraform/     GCP deployment: Cloud Run, Cloud SQL, Pub/Sub, VPC, IAM, Secret Manager
scripts/             bootstrap/seed/purge scripts + GCP deploy script
```

## Run it locally

Requires Docker + Docker Compose v2.20+.

```bash
make up      # builds and starts postgres, pubsub emulator, process-worker, ai-api, referral-api, app-api, web
make seed    # runs ingest-indeed once against seed data (no API keys needed)
```

Then open **http://localhost:8090**. It's signed in as `demo@example.com`
by default (dev-mode auth just trusts an email header locally -- see
"Auth" below) -- set your profile skills, click **Find matches**, generate
a resume for one, try **Find a referral contact**, then approve or decline
outreach in the Outreach tab.

Nothing runs against real Gemini or a real Indeed account unless you set
`GEMINI_API_KEY` / `INDEED_PUBLISHER_ID` + `INDEED_API_KEY` (see
`.env.example`) -- by default:
- `USE_MOCK_AI=true`: embeddings and Gemini calls are replaced with
  deterministic offline stand-ins (`services/common/ai.py`) so matching and
  generation work end to end with no API key and no network call.
- Ingestion uses `services/ingest_indeed/sources/seed_data.py`, a small
  generator of realistic-looking postings, instead of a live API call.

To use real Gemini: set `GEMINI_API_KEY` in a `.env` file (docker-compose
picks it up automatically) and it'll flow through to `process-worker` and
`ai-api`.

### Why some things are stubbed here

- **LinkedIn ingestion is a no-op unless explicitly enabled**
  (`ENABLE_LINKEDIN_SCRAPE=true`). LinkedIn's Terms of Service prohibit
  scraping; whether to run this path at all is a legal/business risk
  decision, not something this codebase should default to. Indeed's
  official partner API is the primary, ToS-permitted path
  (`services/ingest_indeed/sources/indeed_api.py`).
- **Referral contact lookup is mocked**
  (`services/referral_api/main.py`) -- a real implementation needs its own
  scoped, ToS-compliant data source. What's real here is the *isolation*:
  a separate `referral` schema, its own retention TTL
  (`scripts/purge_referral_contacts.py`), and the fact that nothing it
  writes can leave the system without a user clicking **Approve & send**
  in `app-api`.
- **Outbound send is mocked** (`services/app_api/notify.py`) -- logs
  instead of emailing/messaging, since a real send needs a real
  provider's credentials. The approval gate around it is real: nothing
  calls `notify.send()` except the `/outreach/{id}/approve` route, and
  only after a user-initiated request.

## Running tests

```bash
pip install -r requirements-dev.txt
make test
```

These are unit tests only (no Postgres/Pub/Sub needed) -- they check the
mock embedding/AI helpers, the pgvector literal formatting, and the seed
data generator. Integration testing is `make up && make seed` plus using
the UI or hitting `app-api` directly.

## Deploying to GCP

`infra/terraform/` stands up the real thing: Cloud SQL (Postgres +
pgvector, HA optional via `cloud_sql_high_availability`), Pub/Sub topics +
DLQ, a private VPC + Serverless VPC Access connector, Cloud Run services
and Jobs, Secret Manager, Cloud Scheduler, and per-service IAM.

```bash
export GCP_PROJECT_ID=your-project
export GCP_REGION=us-central1          # optional, this is the default
export TF_VAR_db_password=$(openssl rand -base64 24)
./scripts/deploy_gcp.sh
```

This builds and pushes every service image to Artifact Registry, applies
the Terraform stack, and runs the DB migrations. See `.env.example` for
the optional real-credential variables (Gemini, Indeed, Firebase project).

**Heads up if you're doing this inside a short-lived lab/sandbox project**
(e.g. a Qwiklabs-style temporary project): the private VPC peering +
Cloud SQL private-IP setup here can take a while to provision and needs
`servicenetworking.googleapis.com` enabled, which some locked-down sandbox
projects restrict. If time is tight, `docker-compose` is the faster path
to something demoable, and you can point `scripts/deploy_gcp.sh` at a
regular (non-sandbox) project later.

### What Terraform does *not* decide for you

Two things from the architecture review are legal/business calls, not
engineering ones, and Terraform won't paper over them:
- `enable_linkedin_scrape` defaults to `false`. Only flip it after an
  actual legal risk-acceptance decision.
- The referral-contact retention period
  (`db/migrations/002_referral_contacts.sql`, default 90 days) is a
  placeholder. The real number and its lawful basis need legal sign-off.

## Auth

Locally, every service trusts an `X-User-Email` header (`AUTH_MODE=dev`)
-- there is no real login, by design, so the whole stack runs without a
Firebase project. `web/app.js` reads the email from a plain text field for
this reason. On Cloud Run, `AUTH_MODE=firebase` switches every service to
verifying a real Firebase/Identity Platform ID token
(`services/common/auth.py`) -- wire up Firebase Auth in the web frontend
before this goes anywhere near real users.

## Architecture reference

The full write-up -- what changed between v1/v2/v3 and why -- lives in the
architecture report generated alongside this repo. Ask for it if you don't
have the link handy.
