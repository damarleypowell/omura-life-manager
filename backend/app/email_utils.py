"""
Shared email sending utility — avoids circular imports.
Used by outreach_ai, automation jobs, and main.py endpoints.
"""
from __future__ import annotations
from datetime import datetime
from backend.app.config import settings


def send_via_sendgrid(to: str, subject: str, body: str, cc: str = None, html_body: str = None) -> dict:
    """Send an email via SendGrid API."""
    import sendgrid as _sg
    from sendgrid.helpers.mail import Mail, Content

    api_key = settings.SENDGRID_API_KEY
    from_email = settings.DEFAULT_FROM_EMAIL or settings.GMAIL_USER
    if not api_key:
        raise ValueError("SENDGRID_API_KEY not configured in .env")
    if not from_email:
        raise ValueError("DEFAULT_FROM_EMAIL not configured in .env")

    client = _sg.SendGridAPIClient(api_key=api_key)
    message = Mail(from_email=from_email, to_emails=to, subject=subject)
    message.add_content(Content("text/plain", body))
    if html_body:
        message.add_content(Content("text/html", html_body))
    if cc:
        from sendgrid.helpers.mail import Cc
        message.cc = Cc(cc)

    response = client.send(message)
    if response.status_code not in (200, 201, 202):
        raise Exception(f"SendGrid returned status {response.status_code}: {response.body}")

    return {
        "sent": True, "to": to, "subject": subject,
        "provider": "sendgrid", "status_code": response.status_code,
        "timestamp": datetime.utcnow().isoformat(),
    }
