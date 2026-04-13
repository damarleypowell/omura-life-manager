"""
Shared Google OAuth token management and Gmail body extraction.
Avoids circular imports between main.py and scheduler_jobs.py.
"""
from __future__ import annotations
import base64
import re
from datetime import datetime
from typing import Optional

import httpx

from backend.app.config import settings

_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def get_google_access_token() -> Optional[str]:
    """Return a valid Google access token, refreshing if needed."""
    from backend.app.utils.security import get_token, store_token

    token = get_token("google")
    if not token:
        return None

    refresh_token = token.get("refresh_token")
    if not refresh_token:
        return token.get("access_token")

    try:
        resp = httpx.post(_GOOGLE_TOKEN_URL, data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        if resp.status_code == 200:
            new_token = resp.json()
            new_token["refresh_token"] = refresh_token
            new_token["stored_at"] = datetime.utcnow().isoformat()
            store_token("google", new_token)
            return new_token["access_token"]
    except Exception:
        pass

    return token.get("access_token")


def _strip_html_clean(html: str) -> str:
    """Strip HTML tags and style/script content, return plain text."""
    # Remove style and script blocks entirely (content inside is CSS/JS, not text)
    html = re.sub(r'<(style|script)[^>]*>.*?</(style|script)>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    # Strip remaining tags
    html = re.sub(r'<[^>]+>', ' ', html)
    return re.sub(r'\s+', ' ', html).strip()


def extract_email_body(payload: dict) -> str:
    """Recursively extract plain text from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == "text/plain" and body_data:
        return base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")

    if mime_type == "text/html" and body_data:
        raw = base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")
        return _strip_html_clean(raw)

    parts = payload.get("parts", [])
    plain = ""
    html_fallback = ""
    for part in parts:
        result = extract_email_body(part)
        if part.get("mimeType", "").startswith("text/plain") and not plain:
            plain = result
        elif part.get("mimeType", "").startswith("text/html") and not html_fallback:
            html_fallback = result
        elif not plain and result:
            plain = result

    return plain or html_fallback
