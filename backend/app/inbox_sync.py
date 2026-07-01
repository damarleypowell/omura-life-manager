"""Live inbox sync.

Pulls recent Gmail INBOX messages into the ``Communication`` table so the
InboxAI agent and the unified inbox operate on the user's REAL mail instead of
an empty/stale table. Shared by the ``/api/sync/emails`` endpoint and by
``InboxAI.process_inbox`` (which calls it first, so "check my inbox" actually
fetches live email).

Requires a connected Google account (OAuth via ``/auth/google``, scope
``gmail.readonly``). When no token is present it returns a clear
``not_connected`` status rather than silently doing nothing.
"""
from __future__ import annotations

from datetime import datetime

import httpx

from backend.app.database import models
from backend.app.google_utils import get_google_access_token, extract_email_body

_GMAIL_LIST = "https://gmail.googleapis.com/gmail/v1/users/me/messages"


def sync_gmail_inbox(db, max_results: int = 30) -> dict:
    """Fetch up to ``max_results`` recent INBOX messages into Communication.

    Returns a status dict: ``{"status": "success"|"not_connected"|"error",
    "synced": <int>, ...}``. New messages are inserted; already-synced ones
    (matched by Gmail ``external_id``) have their body/subject/sender refreshed.
    """
    access_token = get_google_access_token()
    if not access_token:
        return {
            "status": "not_connected",
            "synced": 0,
            "message": "Connect Google at /auth/google to read your inbox.",
        }

    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        list_resp = httpx.get(
            _GMAIL_LIST, headers=headers,
            params={"maxResults": max_results, "labelIds": "INBOX"}, timeout=30,
        )
        if list_resp.status_code in (401, 403):
            # Token expired / revoked / insufficient scope — actionable as a reconnect.
            return {
                "status": "not_connected",
                "synced": 0,
                "message": "Google access expired — reconnect at /auth/google to read your inbox.",
            }
        if list_resp.status_code != 200:
            return {"status": "error", "synced": 0, "message": list_resp.text[:200]}

        message_ids = [m["id"] for m in list_resp.json().get("messages", [])]
        saved = 0

        for msg_id in message_ids[:max_results]:
            existing = (
                db.query(models.Communication)
                .filter(models.Communication.external_id == msg_id)
                .first()
            )

            msg_resp = httpx.get(
                f"{_GMAIL_LIST}/{msg_id}", headers=headers,
                params={"format": "full"}, timeout=30,
            )
            if msg_resp.status_code != 200:
                continue

            msg = msg_resp.json()
            header_map = {
                h["name"].lower(): h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }
            subject = header_map.get("subject", "(no subject)")
            sender = header_map.get("from", "unknown")
            recipient = header_map.get("to", "")
            date_str = header_map.get("date", "")
            body = extract_email_body(msg.get("payload", {}))
            labels = msg.get("labelIds", [])
            is_unread = "UNREAD" in labels

            try:
                received_at = (
                    datetime.strptime(date_str[:25].strip(), "%a, %d %b %Y %H:%M:%S")
                    if date_str else datetime.utcnow()
                )
            except Exception:
                received_at = datetime.utcnow()

            if existing:
                existing.body = body[:10000]
                existing.subject = subject[:500]
                existing.sender = sender[:255]
            else:
                db.add(models.Communication(
                    platform="gmail",
                    external_id=msg_id,
                    sender=sender[:255],
                    recipient=recipient[:255],
                    subject=subject[:500],
                    body=body[:10000],
                    is_read=not is_unread,
                    labels=labels,
                    received_at=received_at,
                ))
                saved += 1

        db.commit()
        return {
            "status": "success",
            "synced": saved,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        db.rollback()
        return {"status": "error", "synced": 0, "message": str(exc)}
