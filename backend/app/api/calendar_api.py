"""
Omura Calendar, Task, and Knowledge API Integrations
Async-ready clients for Google Calendar, Todoist, and Notion.
Each client normalizes data into CalendarEvent, Task, and Note schemas
for unified schedule/task/knowledge management.

All methods return mock data during development.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


# ═══════════════════════════════════════════════════════════════════════
#  Google Calendar
# ═══════════════════════════════════════════════════════════════════════

class GoogleCalendarClient:
    """Async-ready client for the Google Calendar API v3.

    Handles event CRUD and normalizes calendar data into the
    Omura CalendarEvent schema.
    """

    BASE_URL = "https://www.googleapis.com/calendar/v3"

    def __init__(self) -> None:
        self.client_id: Optional[str] = settings.GOOGLE_CLIENT_ID
        self.client_secret: Optional[str] = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri: str = settings.GOOGLE_REDIRECT_URI
        self.access_token: Optional[str] = None
        self.calendar_id: str = "primary"
        self._http: httpx.AsyncClient = httpx.AsyncClient(timeout=30.0)
        self._logger = OmuraLogger("google_calendar_client")
        self._logger.info("GoogleCalendarClient initialized")

    async def authenticate(self, auth_code: Optional[str] = None) -> Dict[str, Any]:
        """Exchange an OAuth code for Google Calendar API access tokens.

        Args:
            auth_code: Authorization code from Google's OAuth consent screen
                with Calendar scopes.

        Returns:
            Token payload with ``access_token`` and expiry information.
        """
        self._logger.info("Authenticating with Google Calendar API", auth_code_provided=bool(auth_code))
        self.access_token = "mock_gcal_access_token"
        return {
            "access_token": self.access_token,
            "refresh_token": "mock_gcal_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    async def fetch_events(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Retrieve upcoming calendar events within the specified window.

        Args:
            days_ahead: Number of days ahead to look for events.

        Returns:
            List of CalendarEvent-schema dicts.
        """
        self._logger.info("Fetching Google Calendar events", days_ahead=days_ahead)
        now = datetime.utcnow()
        events = [
            {
                "external_id": "gcal_event_001",
                "title": "Weekly Team Standup",
                "description": "Review progress on Q1 goals and blockers.",
                "location": "Google Meet",
                "start_time": (now + timedelta(hours=2)).isoformat(),
                "end_time": (now + timedelta(hours=2, minutes=30)).isoformat(),
                "is_all_day": False,
                "source": "google_calendar",
                "metadata": {
                    "calendar_id": self.calendar_id,
                    "recurrence": "RRULE:FREQ=WEEKLY;BYDAY=MO",
                    "attendees": ["team@example.com"],
                },
            },
            {
                "external_id": "gcal_event_002",
                "title": "Client Strategy Call - Acme Corp",
                "description": "Discuss content strategy and ad budget for Q2.",
                "location": "Zoom",
                "start_time": (now + timedelta(days=1, hours=10)).isoformat(),
                "end_time": (now + timedelta(days=1, hours=11)).isoformat(),
                "is_all_day": False,
                "source": "google_calendar",
                "metadata": {
                    "calendar_id": self.calendar_id,
                    "attendees": ["client@acme.com", "user@example.com"],
                },
            },
            {
                "external_id": "gcal_event_003",
                "title": "Content Shoot Day",
                "description": "Full-day content production for Instagram and TikTok.",
                "location": "Studio A",
                "start_time": (now + timedelta(days=3)).replace(hour=9, minute=0).isoformat(),
                "end_time": (now + timedelta(days=3)).replace(hour=17, minute=0).isoformat(),
                "is_all_day": True,
                "source": "google_calendar",
                "metadata": {"calendar_id": self.calendar_id},
            },
            {
                "external_id": "gcal_event_004",
                "title": "Dentist Appointment",
                "description": "Regular checkup.",
                "location": "123 Main St, Suite 200",
                "start_time": (now + timedelta(days=5, hours=14)).isoformat(),
                "end_time": (now + timedelta(days=5, hours=15)).isoformat(),
                "is_all_day": False,
                "source": "google_calendar",
                "metadata": {"calendar_id": self.calendar_id, "category": "personal"},
            },
        ]
        # Filter to only events within the window
        cutoff = now + timedelta(days=days_ahead)
        events = [e for e in events if datetime.fromisoformat(e["start_time"]) <= cutoff]
        self._logger.info("Fetched Google Calendar events", count=len(events))
        return events

    async def create_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new event on the Google Calendar.

        Args:
            data: Event data containing:
                - ``title``: Event title.
                - ``start_time``: ISO-format start datetime.
                - ``end_time``: ISO-format end datetime.
                - ``description``: Optional description.
                - ``location``: Optional location.
                - ``attendees``: Optional list of email addresses.

        Returns:
            Created CalendarEvent-schema dict with assigned ``external_id``.
        """
        self._logger.info("Creating Google Calendar event", title=data.get("title"))
        result = {
            "external_id": "gcal_event_new_001",
            "title": data.get("title", "Untitled Event"),
            "description": data.get("description"),
            "location": data.get("location"),
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "is_all_day": data.get("is_all_day", False),
            "source": "google_calendar",
            "metadata": {"calendar_id": self.calendar_id},
            "created_at": datetime.utcnow().isoformat(),
        }
        self._logger.info("Google Calendar event created", event_id=result["external_id"])
        return result

    async def update_event(self, event_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing Google Calendar event.

        Args:
            event_id: The calendar event's external ID.
            data: Fields to update (any subset of create_event fields).

        Returns:
            Updated CalendarEvent-schema dict.
        """
        self._logger.info("Updating Google Calendar event", event_id=event_id)
        result = {
            "external_id": event_id,
            "title": data.get("title", "Updated Event"),
            "description": data.get("description"),
            "location": data.get("location"),
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "is_all_day": data.get("is_all_day", False),
            "source": "google_calendar",
            "metadata": {"calendar_id": self.calendar_id},
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._logger.info("Google Calendar event updated", event_id=event_id)
        return result

    async def delete_event(self, event_id: str) -> Dict[str, Any]:
        """Delete an event from Google Calendar.

        Args:
            event_id: The calendar event's external ID.

        Returns:
            Deletion confirmation with ``status``.
        """
        self._logger.info("Deleting Google Calendar event", event_id=event_id)
        result = {
            "external_id": event_id,
            "status": "deleted",
            "deleted_at": datetime.utcnow().isoformat(),
        }
        self._logger.info("Google Calendar event deleted", event_id=event_id)
        return result

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
        self._logger.info("GoogleCalendarClient HTTP connection closed")


# ═══════════════════════════════════════════════════════════════════════
#  Todoist
# ═══════════════════════════════════════════════════════════════════════

class TodoistClient:
    """Async-ready client for the Todoist REST API v2.

    Manages tasks and projects, normalizing data into the Omura Task schema.
    """

    BASE_URL = "https://api.todoist.com/rest/v2"

    def __init__(self) -> None:
        self.api_key: Optional[str] = settings.TODOIST_API_KEY
        self._http: httpx.AsyncClient = httpx.AsyncClient(timeout=30.0)
        self._logger = OmuraLogger("todoist_client")
        self._logger.info("TodoistClient initialized")

    async def authenticate(self) -> Dict[str, Any]:
        """Validate the Todoist API key and retrieve user information.

        Returns:
            User profile information confirming the key is valid.
        """
        self._logger.info("Authenticating with Todoist API")
        return {
            "user_id": "mock_todoist_user_001",
            "email": "user@example.com",
            "full_name": "Omura User",
            "api_key_valid": True,
        }

    async def fetch_tasks(
        self,
        project_id: Optional[str] = None,
        filter_query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch active tasks from Todoist.

        Args:
            project_id: Optional project ID to filter tasks.
            filter_query: Optional Todoist filter string (e.g. ``"today | overdue"``).

        Returns:
            List of Task-schema dicts.
        """
        self._logger.info(
            "Fetching Todoist tasks",
            project_id=project_id,
            filter_query=filter_query,
        )
        now = datetime.utcnow()
        tasks = [
            {
                "title": "Review Q1 financial report",
                "description": "Go through QuickBooks export and flag discrepancies.",
                "status": "todo",
                "priority": "high",
                "due_date": (now + timedelta(days=1)).isoformat(),
                "source": "todoist",
                "external_id": "todoist_task_001",
                "metadata": {
                    "project_name": "Finance",
                    "labels": ["urgent", "finance"],
                    "todoist_priority": 4,
                },
            },
            {
                "title": "Write blog post draft",
                "description": "Draft the SEO article on digital marketing trends.",
                "status": "in_progress",
                "priority": "medium",
                "due_date": (now + timedelta(days=3)).isoformat(),
                "source": "todoist",
                "external_id": "todoist_task_002",
                "metadata": {
                    "project_name": "Content",
                    "labels": ["writing", "content"],
                    "todoist_priority": 3,
                },
            },
            {
                "title": "Schedule Instagram posts for next week",
                "description": "Use the content calendar to queue 5 posts.",
                "status": "todo",
                "priority": "medium",
                "due_date": (now + timedelta(days=2)).isoformat(),
                "source": "todoist",
                "external_id": "todoist_task_003",
                "metadata": {
                    "project_name": "Social Media",
                    "labels": ["social", "instagram"],
                    "todoist_priority": 3,
                },
            },
            {
                "title": "Grocery shopping",
                "description": "Pick up items on the shared list.",
                "status": "todo",
                "priority": "low",
                "due_date": (now + timedelta(days=1)).isoformat(),
                "source": "todoist",
                "external_id": "todoist_task_004",
                "metadata": {
                    "project_name": "Personal",
                    "labels": ["errands"],
                    "todoist_priority": 1,
                },
            },
        ]
        self._logger.info("Fetched Todoist tasks", count=len(tasks))
        return tasks

    async def create_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task in Todoist.

        Args:
            data: Task data containing:
                - ``title``: Task content / title.
                - ``description``: Optional description.
                - ``due_date``: Optional ISO-format due date.
                - ``priority``: Priority level (``"low"``, ``"medium"``,
                  ``"high"``, ``"critical"``).
                - ``project_name``: Optional Todoist project name.
                - ``labels``: Optional list of label names.

        Returns:
            Created Task-schema dict with assigned ``external_id``.
        """
        self._logger.info("Creating Todoist task", title=data.get("title"))
        result = {
            "title": data.get("title", "Untitled Task"),
            "description": data.get("description"),
            "status": "todo",
            "priority": data.get("priority", "medium"),
            "due_date": data.get("due_date"),
            "source": "todoist",
            "external_id": "todoist_task_new_001",
            "metadata": {
                "project_name": data.get("project_name"),
                "labels": data.get("labels", []),
            },
            "created_at": datetime.utcnow().isoformat(),
        }
        self._logger.info("Todoist task created", task_id=result["external_id"])
        return result

    async def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Mark a Todoist task as completed.

        Args:
            task_id: The Todoist task ID to complete.

        Returns:
            Completion confirmation with updated ``status``.
        """
        self._logger.info("Completing Todoist task", task_id=task_id)
        result = {
            "external_id": task_id,
            "status": "done",
            "completed_at": datetime.utcnow().isoformat(),
        }
        self._logger.info("Todoist task completed", task_id=task_id)
        return result

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
        self._logger.info("TodoistClient HTTP connection closed")


# ═══════════════════════════════════════════════════════════════════════
#  Notion
# ═══════════════════════════════════════════════════════════════════════

class NotionClient:
    """Async-ready client for the Notion API v1.

    Manages pages and databases, normalizing data into the Omura Note schema
    for the knowledge hub.
    """

    BASE_URL = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    def __init__(self) -> None:
        self.api_key: Optional[str] = settings.NOTION_API_KEY
        self._http: httpx.AsyncClient = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Notion-Version": self.NOTION_VERSION,
                "Content-Type": "application/json",
            },
        )
        self._logger = OmuraLogger("notion_client")
        self._logger.info("NotionClient initialized")

    async def authenticate(self) -> Dict[str, Any]:
        """Validate the Notion integration token and retrieve bot user info.

        Returns:
            Bot user information confirming the token is valid.
        """
        self._logger.info("Authenticating with Notion API")
        return {
            "bot_id": "mock_notion_bot_001",
            "workspace_name": "Omura Workspace",
            "workspace_id": "mock_ws_12345",
            "api_key_valid": True,
        }

    async def fetch_pages(self, max_results: int = 20) -> List[Dict[str, Any]]:
        """Fetch recently edited Notion pages.

        Args:
            max_results: Maximum number of pages to return.

        Returns:
            List of Note-schema dicts.
        """
        self._logger.info("Fetching Notion pages", max_results=max_results)
        now = datetime.utcnow()
        pages = [
            {
                "title": "Q1 2026 Strategy Document",
                "content": "Strategic priorities:\n1. Scale content production\n2. Launch ad campaigns\n3. Improve conversion funnel",
                "category": "strategy",
                "tags": ["strategy", "Q1", "planning"],
                "source": "notion",
                "external_id": "notion_page_001",
                "metadata": {
                    "database_id": "notion_db_strategies",
                    "last_edited_by": "user",
                    "icon": "🎯",
                },
                "updated_at": (now - timedelta(hours=3)).isoformat(),
            },
            {
                "title": "Content Ideas Backlog",
                "content": "- 10 tips for productivity\n- Behind the scenes studio tour\n- Interview series with founders\n- Monthly analytics review",
                "category": "idea",
                "tags": ["content", "ideas", "backlog"],
                "source": "notion",
                "external_id": "notion_page_002",
                "metadata": {
                    "database_id": "notion_db_content",
                    "last_edited_by": "user",
                },
                "updated_at": (now - timedelta(days=1)).isoformat(),
            },
            {
                "title": "Meeting Notes: Investor Call 2026-03-20",
                "content": "Attendees: CEO, CFO, Lead Investor\n\nKey takeaways:\n- Revenue target approved\n- Need to present updated metrics by April 1",
                "category": "meeting_notes",
                "tags": ["meetings", "investors", "finance"],
                "source": "notion",
                "external_id": "notion_page_003",
                "metadata": {
                    "database_id": "notion_db_meetings",
                    "last_edited_by": "user",
                },
                "updated_at": (now - timedelta(days=4)).isoformat(),
            },
        ]
        self._logger.info("Fetched Notion pages", count=len(pages))
        return pages

    async def create_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Notion page.

        Args:
            data: Page data containing:
                - ``title``: Page title.
                - ``content``: Page content as plain text or markdown.
                - ``category``: Note category (e.g. ``"research"``, ``"strategy"``).
                - ``tags``: Optional list of tags.
                - ``database_id``: Optional parent database ID.

        Returns:
            Created Note-schema dict with assigned ``external_id``.
        """
        self._logger.info("Creating Notion page", title=data.get("title"))
        result = {
            "title": data.get("title", "Untitled"),
            "content": data.get("content", ""),
            "category": data.get("category", "research"),
            "tags": data.get("tags", []),
            "source": "notion",
            "external_id": "notion_page_new_001",
            "metadata": {
                "database_id": data.get("database_id"),
                "last_edited_by": "omura_bot",
            },
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._logger.info("Notion page created", page_id=result["external_id"])
        return result

    async def fetch_databases(self) -> List[Dict[str, Any]]:
        """List all Notion databases shared with the integration.

        Returns:
            List of database summary dicts with ID, title, and property schema.
        """
        self._logger.info("Fetching Notion databases")
        databases = [
            {
                "id": "notion_db_strategies",
                "title": "Strategies",
                "description": "Strategic planning documents and goals.",
                "properties": {
                    "Name": {"type": "title"},
                    "Status": {"type": "select"},
                    "Priority": {"type": "select"},
                    "Due Date": {"type": "date"},
                },
                "metadata": {"source": "notion"},
            },
            {
                "id": "notion_db_content",
                "title": "Content Pipeline",
                "description": "Content ideas, drafts, and publishing schedule.",
                "properties": {
                    "Name": {"type": "title"},
                    "Status": {"type": "select"},
                    "Platform": {"type": "multi_select"},
                    "Publish Date": {"type": "date"},
                },
                "metadata": {"source": "notion"},
            },
            {
                "id": "notion_db_meetings",
                "title": "Meeting Notes",
                "description": "Notes and action items from meetings.",
                "properties": {
                    "Name": {"type": "title"},
                    "Date": {"type": "date"},
                    "Attendees": {"type": "multi_select"},
                    "Action Items": {"type": "rich_text"},
                },
                "metadata": {"source": "notion"},
            },
        ]
        self._logger.info("Fetched Notion databases", count=len(databases))
        return databases

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
        self._logger.info("NotionClient HTTP connection closed")
