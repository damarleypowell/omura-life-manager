"""
Omura Gmail API Integration
Provides async-ready Gmail client for fetching, sending, labeling, and
searching emails. Normalizes raw Gmail data into the Communication schema.

All methods return mock data during development — swap the placeholder
implementations for real httpx calls when OAuth credentials are configured.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger

logger = OmuraLogger("gmail_client")


class GmailClient:
    """Async-ready client for the Gmail REST API (v1).

    Handles OAuth 2.0 authentication, email CRUD, label management,
    and full-text search. Every returned email is normalized to the
    Omura Communication schema so the unified inbox can consume it
    without platform-specific logic.
    """

    BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(self) -> None:
        self.client_id: Optional[str] = settings.GOOGLE_CLIENT_ID
        self.client_secret: Optional[str] = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri: str = settings.GOOGLE_REDIRECT_URI
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self._http: httpx.AsyncClient = httpx.AsyncClient(
            timeout=30.0,
            headers={"Accept": "application/json"},
        )
        logger.info("GmailClient initialized")

    # ── Authentication ──────────────────────────────────────────────

    async def authenticate(self, auth_code: Optional[str] = None) -> Dict[str, Any]:
        """Exchange an OAuth authorization code for access + refresh tokens.

        Args:
            auth_code: The authorization code returned by Google's consent
                screen. Pass ``None`` during development to use mock tokens.

        Returns:
            A dict with ``access_token``, ``refresh_token``, and
            ``expires_in`` fields.
        """
        logger.info("Authenticating with Gmail API", auth_code_provided=bool(auth_code))

        # --- placeholder: return mock tokens ---
        self.access_token = "mock_access_token_gmail"
        self.refresh_token = "mock_refresh_token_gmail"
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    # ── Fetch Emails ────────────────────────────────────────────────

    async def fetch_emails(self, max_results: int = 50) -> List[Dict[str, Any]]:
        """Retrieve the most recent emails from the user's inbox.

        Args:
            max_results: Maximum number of messages to return (1-500).

        Returns:
            A list of dicts conforming to the Communication schema.
        """
        logger.info("Fetching emails", max_results=max_results)

        # --- placeholder: return mock emails ---
        now = datetime.utcnow()
        mock_emails = [
            self._normalize_to_communication(
                external_id=f"gmail_msg_{i}",
                sender=f"sender{i}@example.com",
                recipient="user@example.com",
                subject=f"Mock Email Subject #{i}",
                body=f"This is the body of mock email #{i}. It contains important information.",
                labels=["INBOX"],
                received_at=(now - timedelta(hours=i)).isoformat(),
            )
            for i in range(1, min(max_results, 6) + 1)
        ]
        logger.info("Fetched emails successfully", count=len(mock_emails))
        return mock_emails

    # ── Send Email ──────────────────────────────────────────────────

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Compose and send an email through the Gmail API.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body: Plain-text or HTML email body.
            cc: Optional list of CC recipients.
            bcc: Optional list of BCC recipients.

        Returns:
            A dict containing the sent message's ``id`` and ``threadId``.
        """
        logger.info("Sending email", to=to, subject=subject)

        # --- placeholder: return mock send confirmation ---
        result = {
            "id": "mock_sent_msg_001",
            "threadId": "mock_thread_001",
            "labelIds": ["SENT"],
            "status": "sent",
        }
        logger.info("Email sent successfully", message_id=result["id"])
        return result

    # ── Label Email ─────────────────────────────────────────────────

    async def label_email(self, email_id: str, label: str) -> Dict[str, Any]:
        """Apply a label to an existing email message.

        Args:
            email_id: The Gmail message ID.
            label: Label name to apply (e.g. ``"IMPORTANT"``, ``"STARRED"``).

        Returns:
            A dict echoing the updated message ID and its current labels.
        """
        logger.info("Labeling email", email_id=email_id, label=label)

        # --- placeholder ---
        result = {
            "id": email_id,
            "labelIds": ["INBOX", label],
            "status": "updated",
        }
        logger.info("Email labeled successfully", email_id=email_id, label=label)
        return result

    # ── Search Emails ───────────────────────────────────────────────

    async def search_emails(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Full-text search across the user's mailbox using Gmail query syntax.

        Args:
            query: Gmail search query (e.g. ``"from:boss subject:report"``).
            max_results: Maximum results to return.

        Returns:
            A list of Communication-schema dicts matching the query.
        """
        logger.info("Searching emails", query=query, max_results=max_results)

        # --- placeholder ---
        now = datetime.utcnow()
        results = [
            self._normalize_to_communication(
                external_id="gmail_search_001",
                sender="match@example.com",
                recipient="user@example.com",
                subject=f"Search result for: {query}",
                body="This email matched your search query.",
                labels=["INBOX"],
                received_at=now.isoformat(),
            )
        ]
        logger.info("Search complete", query=query, results_count=len(results))
        return results

    # ── Get Single Email ────────────────────────────────────────────

    async def get_email(self, email_id: str) -> Dict[str, Any]:
        """Retrieve a single email by its Gmail message ID.

        Args:
            email_id: The Gmail message ID.

        Returns:
            A Communication-schema dict for the requested message.
        """
        logger.info("Fetching single email", email_id=email_id)

        # --- placeholder ---
        email = self._normalize_to_communication(
            external_id=email_id,
            sender="someone@example.com",
            recipient="user@example.com",
            subject="Mock Single Email",
            body="Full body content of the requested email.",
            labels=["INBOX", "IMPORTANT"],
            received_at=datetime.utcnow().isoformat(),
        )
        logger.info("Email fetched successfully", email_id=email_id)
        return email

    # ── Data Normalization ──────────────────────────────────────────

    @staticmethod
    def _normalize_to_communication(
        external_id: str,
        sender: str,
        recipient: str,
        subject: str,
        body: str,
        labels: List[str],
        received_at: str,
    ) -> Dict[str, Any]:
        """Transform raw Gmail message data into the Omura Communication schema.

        Returns:
            A flat dict that can be passed directly to
            ``Communication(**data)`` for ORM insertion.
        """
        return {
            "platform": "gmail",
            "external_id": external_id,
            "sender": sender,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "summary": None,
            "urgency": "low",
            "is_read": False,
            "is_flagged": "STARRED" in labels or "IMPORTANT" in labels,
            "ai_suggested_response": None,
            "labels": labels,
            "metadata": {
                "source": "gmail_api",
                "raw_label_ids": labels,
            },
            "received_at": received_at,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

    # ── Cleanup ─────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the underlying HTTP client connection pool."""
        await self._http.aclose()
        logger.info("GmailClient HTTP connection closed")
