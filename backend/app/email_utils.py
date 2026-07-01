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

import logging as _logging
from backend.app.config import settings

_send_log = _logging.getLogger("email_utils")


def send_via_sendgrid(to: str, subject: str, body: str, cc: str = None, html_body: str = None) -> dict:
    """Send email FROM ironlogic.business@gmail.com.

    Primary: Gmail SMTP (app password — works locally, no OAuth). Fallbacks:
    Resend (verified domain ironlogic.cc), then Gmail API (if OAuth is valid).

    Function name kept as send_via_sendgrid to avoid breaking all callers.
    """
    errors: list[str] = []

    # ── Primary: Gmail SMTP — sends as ironlogic.business@gmail.com ──
    try:
        return _send_via_smtp(to, subject, body, cc, html_body)
    except Exception as _smtp_e:
        errors.append(f"Gmail SMTP: {_smtp_e}")
        _send_log.warning("Gmail SMTP failed, trying Resend fallback: %s", _smtp_e)

    # ── Fallback 1: Resend (verified domain ironlogic.cc) ──
    if settings.RESEND_API_KEY:
        try:
            return _send_via_resend(to, subject, body, cc, html_body)
        except Exception as _re:
            errors.append(f"Resend: {_re}")
            _send_log.warning("Resend send failed, trying Gmail API fallback: %s", _re)

    # ── Fallback 2: Gmail API (requires a valid Google OAuth token) ──
    try:
        from backend.app.google_utils import get_google_access_token
        access_token = get_google_access_token()
        if access_token:
            return _send_via_gmail_api(access_token, to, subject, body, cc, html_body)
        else:
            errors.append("Gmail API: no Google OAuth token — visit /auth/google to reconnect")
    except Exception as _e:
        errors.append(f"Gmail API: {_e}")

    raise RuntimeError("Email delivery failed — " + "; ".join(f"[{e}]" for e in errors))


def _send_via_resend(to: str, subject: str, body: str, cc: str = None, html_body: str = None) -> dict:
    """Send via the Resend HTTPS API (https://resend.com)."""
    from_addr = settings.RESEND_FROM or settings.DEFAULT_FROM_EMAIL
    payload: dict = {"from": from_addr, "to": [to], "subject": subject, "text": body}
    if html_body:
        payload["html"] = html_body
    if cc:
        payload["cc"] = [cc]

    resp = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    if resp.status_code not in (200, 201, 202):
        raise Exception(f"Resend API error {resp.status_code}: {resp.text[:200]}")

    data = resp.json() if resp.content else {}
    return {
        "sent": True, "to": to, "subject": subject,
        "provider": "resend", "id": data.get("id"),
        "status_code": resp.status_code,
        "timestamp": datetime.utcnow().isoformat(),
    }


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
