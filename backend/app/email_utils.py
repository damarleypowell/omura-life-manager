"""
Shared email sending utility — uses Gmail SMTP.
"""
from __future__ import annotations
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from backend.app.config import settings


def send_via_sendgrid(to: str, subject: str, body: str, cc: str = None, html_body: str = None) -> dict:
    """Send email via Gmail SMTP (function kept as send_via_sendgrid to avoid breaking callers)."""
    gmail_user = settings.GMAIL_USER
    gmail_password = settings.GMAIL_APP_PASSWORD

    if not gmail_user or not gmail_password:
        raise ValueError("GMAIL_USER and GMAIL_APP_PASSWORD must be set")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = to
    if cc:
        msg["Cc"] = cc

    msg.attach(MIMEText(body, "plain"))
    if html_body:
        msg.attach(MIMEText(html_body, "html"))

    recipients = [to] + ([cc] if cc else [])
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipients, msg.as_string())

    return {
        "sent": True, "to": to, "subject": subject,
        "provider": "gmail", "status_code": 200,
        "timestamp": datetime.utcnow().isoformat(),
    }
