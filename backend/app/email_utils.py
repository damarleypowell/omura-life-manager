"""
Shared email sending utility — uses Gmail API (OAuth) with SMTP fallback.
"""
from __future__ import annotations
import base64
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx

from backend.app.config import settings


def send_via_sendgrid(to: str, subject: str, body: str, cc: str = None, html_body: str = None) -> dict:
    """Send email. Uses Gmail API (OAuth token) if connected, falls back to SMTP.

    Function name kept as send_via_sendgrid to avoid breaking all callers.
    """
    # ── Try Gmail API first (works on Railway — HTTPS, not SMTP) ──
    try:
        from backend.app.google_utils import get_google_access_token
        access_token = get_google_access_token()
        if access_token:
            return _send_via_gmail_api(access_token, to, subject, body, cc, html_body)
    except Exception:
        pass  # Fall through to SMTP

    # ── Fallback: Gmail SMTP (works locally, blocked on Railway) ──
    return _send_via_smtp(to, subject, body, cc, html_body)


def _build_mime(to: str, subject: str, body: str, cc: str = None, html_body: str = None):
    from_addr = settings.GMAIL_USER or "noreply@omura.app"
    if html_body:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
    else:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "plain"))
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    return msg


def _send_via_gmail_api(access_token: str, to: str, subject: str, body: str,
                         cc: str = None, html_body: str = None) -> dict:
    """Send via Gmail REST API — works on Railway (HTTPS, no SMTP firewall)."""
    msg = _build_mime(to, subject, body, cc, html_body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    resp = httpx.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"raw": raw},
        timeout=30,
    )

    if resp.status_code not in (200, 202):
        raise Exception(f"Gmail API error {resp.status_code}: {resp.text[:200]}")

    return {
        "sent": True, "to": to, "subject": subject,
        "provider": "gmail_api", "status_code": resp.status_code,
        "timestamp": datetime.utcnow().isoformat(),
    }


def _send_via_smtp(to: str, subject: str, body: str, cc: str = None, html_body: str = None) -> dict:
    """Send via Gmail SMTP (local dev fallback — blocked on Railway)."""
    gmail_user = settings.GMAIL_USER
    gmail_password = settings.GMAIL_APP_PASSWORD

    if not gmail_user or not gmail_password:
        raise ValueError("No Gmail OAuth token and no GMAIL_USER/GMAIL_APP_PASSWORD configured")

    msg = _build_mime(to, subject, body, cc, html_body)
    recipients = [to] + ([cc] if cc else [])

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipients, msg.as_string())

    return {
        "sent": True, "to": to, "subject": subject,
        "provider": "gmail_smtp", "status_code": 200,
        "timestamp": datetime.utcnow().isoformat(),
    }
