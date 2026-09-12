"""Outbound send integration. This is the only code path in the whole
system that causes something to leave Code Kitchen and reach a third
party -- and it only runs after app-api's approval gate has flipped an
outreach/application row to 'approved'. No auto-send, ever.

Mocked here (logs + returns success) since a real deploy needs a real
email/messaging provider's credentials. Swap send() for a real SMTP/SendGrid/
Twilio call when those exist -- the call site in routes/outreach.py doesn't
need to change.
"""


def send(to_hint: str, subject: str, body: str) -> dict:
    print(f"[notify] SEND -> {to_hint} | {subject}\n{body}")
    return {"sent": True, "provider": "mock"}
