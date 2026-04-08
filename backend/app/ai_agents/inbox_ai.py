"""
Omura Inbox AI Agent
Handles intelligent inbox processing: triage, summarization, urgency detection,
and automated response suggestions for all incoming messages.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


class InboxAI:
    """AI-powered inbox management agent.

    Processes incoming messages across email, social DMs, and internal
    notifications. Triages by urgency, generates summaries, and drafts
    suggested replies to accelerate response time.
    """

    URGENCY_LEVELS = ("critical", "high", "medium", "low", "informational")
    LABEL_CATEGORIES = (
        "client", "invoice", "support", "scheduling", "personal",
        "marketing", "legal", "partnership", "notification", "spam",
    )

    def __init__(self, db_session: Any) -> None:
        """Initialize the InboxAI agent.

        Args:
            db_session: SQLAlchemy database session for querying and
                        persisting inbox data.
        """
        self.db = db_session
        self.logger = OmuraLogger("inbox_ai")
        self.logger.info("InboxAI agent initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def triage_messages(self, messages: list[dict]) -> list[dict]:
        """Categorize a batch of messages by urgency and apply labels.

        Each message dict is expected to contain at minimum:
            - id (int | str)
            - subject (str)
            - body (str)
            - sender (str)

        Returns:
            A list of enriched message dicts, each with added keys:
                - urgency (str): one of URGENCY_LEVELS
                - labels (list[str]): applicable category labels
                - triage_score (float): 0-100 priority score
        """
        self.logger.info(
            "Triaging messages", count=len(messages),
        )
        triaged: list[dict] = []
        for msg in messages:
            prompt = (
                f"Triage the following message.\n"
                f"Subject: {msg.get('subject', '')}\n"
                f"From: {msg.get('sender', '')}\n"
                f"Body: {msg.get('body', '')[:500]}\n"
                f"Return urgency, labels, and a priority score 0-100."
            )
            result = self._call_ai(prompt, context={"task": "triage"})
            enriched = {
                **msg,
                "urgency": result.get("urgency", "medium"),
                "labels": result.get("labels", []),
                "triage_score": result.get("triage_score", 50.0),
            }
            triaged.append(enriched)
            self.logger.debug(
                "Message triaged",
                message_id=msg.get("id"),
                urgency=enriched["urgency"],
                score=enriched["triage_score"],
            )

        triaged.sort(key=lambda m: m["triage_score"], reverse=True)
        self.logger.info(
            "Triage complete",
            total=len(triaged),
            critical=sum(1 for m in triaged if m["urgency"] == "critical"),
        )
        return triaged

    def summarize_message(self, message: dict) -> str:
        """Generate a concise summary of a single message.

        Args:
            message: Dict containing at least 'subject' and 'body'.

        Returns:
            A plain-text summary string (1-3 sentences).
        """
        self.logger.info(
            "Summarizing message", message_id=message.get("id"),
        )
        prompt = (
            f"Summarize this message in 1-3 sentences.\n"
            f"Subject: {message.get('subject', '')}\n"
            f"Body: {message.get('body', '')}"
        )
        result = self._call_ai(prompt, context={"task": "summarize"})
        summary = result.get("summary", "No summary available.")
        self.logger.info(
            "Summary generated",
            message_id=message.get("id"),
            length=len(summary),
        )
        return summary

    def suggest_response(self, message: dict) -> str:
        """Draft a suggested reply to the given message.

        Args:
            message: Dict with 'subject', 'body', 'sender', and
                     optionally 'thread_history' (list of prior messages).

        Returns:
            A draft reply string ready for user review.
        """
        self.logger.info(
            "Generating response suggestion",
            message_id=message.get("id"),
            sender=message.get("sender"),
        )
        thread_context = ""
        if message.get("thread_history"):
            thread_context = "\n---\n".join(
                f"From: {m.get('sender')}\n{m.get('body', '')}"
                for m in message["thread_history"][-3:]
            )

        prompt = (
            f"Draft a professional reply to this message.\n"
            f"Subject: {message.get('subject', '')}\n"
            f"From: {message.get('sender', '')}\n"
            f"Body: {message.get('body', '')}\n"
            f"Thread context:\n{thread_context}"
        )
        result = self._call_ai(prompt, context={"task": "suggest_response"})
        draft = result.get("draft", "")
        self.logger.info(
            "Response suggestion ready",
            message_id=message.get("id"),
            draft_length=len(draft),
        )
        return draft

    def flag_urgent(self, messages: list[dict]) -> list[dict]:
        """Identify and flag urgent items from a list of messages.

        Returns only messages that meet the urgency threshold
        (critical or high), enriched with a 'reason' field explaining
        why the item is flagged.

        Args:
            messages: List of message dicts (raw or already triaged).

        Returns:
            Filtered list containing only urgent messages with an
            added 'urgent_reason' key.
        """
        self.logger.info("Scanning for urgent messages", count=len(messages))

        prompt = (
            f"Review {len(messages)} messages and identify which ones are urgent. "
            f"Subjects: {[m.get('subject', '') for m in messages[:20]]}"
        )
        result = self._call_ai(prompt, context={"task": "flag_urgent"})
        urgent_ids = set(result.get("urgent_ids", []))

        flagged: list[dict] = []
        for msg in messages:
            msg_id = msg.get("id")
            if msg_id in urgent_ids or msg.get("urgency") in ("critical", "high"):
                reason = result.get("reasons", {}).get(
                    str(msg_id), "Detected as high-priority by AI analysis.",
                )
                flagged.append({**msg, "urgent_reason": reason})

        self.logger.info(
            "Urgent scan complete",
            flagged=len(flagged),
            total=len(messages),
        )
        return flagged

    def process_inbox(self) -> dict:
        """Run the full inbox processing pipeline.

        Steps:
            1. Fetch unread messages from the database.
            2. Triage all messages by urgency and category.
            3. Summarize each message.
            4. Generate suggested responses for high-priority items.

        Returns:
            A dict with keys:
                - total_processed (int)
                - triaged (list[dict])
                - summaries (dict[str, str]): message_id -> summary
                - suggested_responses (dict[str, str]): message_id -> draft
                - urgent (list[dict])
                - processed_at (str): ISO timestamp
        """
        self.logger.info("Starting full inbox processing pipeline")

        # Step 1: Fetch unread messages (placeholder DB query)
        unread = self._fetch_unread_messages()
        self.logger.info("Fetched unread messages", count=len(unread))

        if not unread:
            self.logger.info("No unread messages to process")
            return {
                "total_processed": 0,
                "triaged": [],
                "summaries": {},
                "suggested_responses": {},
                "urgent": [],
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }

        # Step 2: Triage
        triaged = self.triage_messages(unread)

        # Step 3: Summarize
        summaries: dict[str, str] = {}
        for msg in triaged:
            msg_id = str(msg.get("id", ""))
            summaries[msg_id] = self.summarize_message(msg)

        # Step 4: Suggest responses for critical / high urgency
        suggested_responses: dict[str, str] = {}
        for msg in triaged:
            if msg.get("urgency") in ("critical", "high"):
                msg_id = str(msg.get("id", ""))
                suggested_responses[msg_id] = self.suggest_response(msg)

        # Step 5: Flag urgent
        urgent = self.flag_urgent(triaged)

        result = {
            "total_processed": len(triaged),
            "triaged": triaged,
            "summaries": summaries,
            "suggested_responses": suggested_responses,
            "urgent": urgent,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

        self.logger.info(
            "Inbox pipeline complete",
            processed=result["total_processed"],
            urgent=len(urgent),
            responses_drafted=len(suggested_responses),
        )
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_unread_messages(self) -> list[dict]:
        """Fetch unread messages from the real communications table."""
        try:
            from backend.app.database.models import Communication
            rows = (
                self.db.query(Communication)
                .filter(Communication.is_read == False)
                .order_by(Communication.received_at.desc())
                .limit(50)
                .all()
            )
            messages = []
            for r in rows:
                messages.append({
                    "id": r.id,
                    "platform": r.platform.value if hasattr(r.platform, "value") else str(r.platform),
                    "sender": r.sender or "",
                    "recipient": r.recipient or "",
                    "subject": r.subject or "",
                    "body": (r.body or "")[:2000],  # truncate for AI
                    "labels": r.labels or [],
                    "received_at": r.received_at.isoformat() if r.received_at else "",
                    "urgency": r.urgency.value if hasattr(r.urgency, "value") else str(r.urgency),
                })
            self.logger.info(f"Fetched {len(messages)} unread messages from DB")
            return messages
        except Exception as exc:
            self.logger.warning("Failed to fetch messages", error=str(exc))
            return []

    def _call_ai(self, prompt: str, context: Optional[dict] = None) -> dict:
        """Call Claude API to process a prompt, with mock fallback.

        Args:
            prompt: The natural-language prompt to send.
            context: Optional metadata about the task type.

        Returns:
            A dict containing the AI response fields.
        """
        task = (context or {}).get("task", "unknown")
        self.logger.debug("Calling AI provider", task=task, prompt_length=len(prompt))

        # Try real Claude API call
        from backend.app.ai_agents._claude_caller import call_claude_json

        system_prompt = (
            "You are an AI inbox management assistant for a personal life & business manager app called Omura. "
            "You analyze messages, triage by urgency, generate summaries, and draft replies. "
            "Always respond with valid JSON only, no markdown wrapping. "
            "Use the exact keys requested in the user prompt."
        )

        task_instructions = {
            "triage": (
                "\n\nRespond with JSON containing: "
                '{"urgency": "critical|high|medium|low|informational", '
                '"labels": ["list","of","category","labels"], '
                '"triage_score": <float 0-100>}'
            ),
            "summarize": (
                "\n\nRespond with JSON containing: "
                '{"summary": "1-3 sentence summary of the message"}'
            ),
            "suggest_response": (
                "\n\nRespond with JSON containing: "
                '{"draft": "the full draft reply text"}'
            ),
            "flag_urgent": (
                "\n\nRespond with JSON containing: "
                '{"urgent_ids": [list of message IDs that are urgent], '
                '"reasons": {"id": "reason why it is urgent"}}'
            ),
        }

        full_prompt = prompt + task_instructions.get(task, "\n\nRespond with valid JSON.")
        result = call_claude_json(full_prompt, system_prompt, agent_name="inbox_ai")

        if result is not None:
            self.logger.debug("Claude API returned valid response for task=%s", task)
            return result

        # ── Fallback: mock responses keyed by task ──
        self.logger.info("Falling back to mock response for task=%s", task)

        if task == "triage":
            is_urgent = any(
                kw in prompt.lower()
                for kw in ("urgent", "asap", "deadline", "overdue", "critical")
            )
            return {
                "urgency": "high" if is_urgent else "medium",
                "labels": ["client", "scheduling"] if is_urgent else ["notification"],
                "triage_score": 85.0 if is_urgent else 45.0,
            }

        if task == "summarize":
            return {
                "summary": (
                    "The sender is requesting a status update on the current "
                    "deliverables and wants to schedule a follow-up call this week."
                ),
            }

        if task == "suggest_response":
            return {
                "draft": (
                    "Hi,\n\n"
                    "Thank you for reaching out. I've reviewed the details and "
                    "will have an update ready by end of day. Would Thursday at "
                    "2 PM work for a quick sync call?\n\n"
                    "Best regards"
                ),
            }

        if task == "flag_urgent":
            return {
                "urgent_ids": [1, 3],
                "reasons": {
                    "1": "Contains time-sensitive deadline reference within 24 hours.",
                    "3": "Client escalation requiring immediate attention.",
                },
            }

        return {"raw": "Mock AI response — task not recognized."}
