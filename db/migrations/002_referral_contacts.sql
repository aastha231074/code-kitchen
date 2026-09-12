-- Referral contact data is personal data about people who never signed up
-- for Code Kitchen. It gets its own schema, its own retention job, and its
-- own IAM scope (granted only to referral-api and app-api) -- see ADR-04.
-- The retention period below is a placeholder; the actual number of days
-- and the lawful basis for holding this data are a legal decision, not an
-- engineering one (see architecture report, section 7).

CREATE SCHEMA IF NOT EXISTS referral;

CREATE TABLE referral.contacts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company             TEXT NOT NULL,
    contact_name        TEXT NOT NULL,
    contact_title       TEXT,
    source_url          TEXT,               -- where the public contact info was found
    discovered_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    retention_expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '90 days')
);

CREATE INDEX contacts_retention_idx ON referral.contacts (retention_expires_at);

-- Run on a schedule (see scripts/purge_referral_contacts.py). Deletes rows
-- past their retention window; nothing here auto-sends anything.
