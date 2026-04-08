"""
Omura Supervisor AI — The Core Brain
=====================================
Central AI agent that acts as Damarley's personal COO / chief of staff.
Uses the Anthropic Claude API with tool-use to manage all aspects of
life and business through the Omura Life Manager platform.

The supervisor can:
- Perform CRUD operations on every database model
- Delegate to specialized agents (inbox, content, project, CRM, etc.)
- Maintain conversational context across sessions
- Request internet access when external data is needed
- Provide prioritized daily briefings and next steps

All actions are logged to the AgentLog table for full auditability.
"""

from __future__ import annotations

import json
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, cast, String

from backend.app.config import settings
from backend.app.database.models import (
    Communication, Project, Task, ContentItem, Metric,
    HealthEntry, Lead, CalendarEvent, Note, AgentLog, Scenario,
    ChatMessage, Credential, InternetRequest, Campaign, ImportedContext,
    UrgencyLevel, TaskStatus, ContentStatus, LeadStatus, Platform,
)
from backend.app.database import crud
from backend.app.utils.logging import OmuraLogger


# ---------------------------------------------------------------------------
# Tool definitions for Claude tool_use
# ---------------------------------------------------------------------------

SUPERVISOR_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "create_task",
        "description": (
            "Create a new task. Optionally assign it to a project. "
            "Use this when Damarley mentions something he needs to do, or when "
            "you identify an action item from conversation context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title for the task."},
                "description": {"type": "string", "description": "Detailed description of what needs to be done."},
                "project_id": {"type": "integer", "description": "ID of the project this task belongs to (optional)."},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Task priority level.",
                },
                "due_date": {"type": "string", "description": "Due date in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)."},
                "status": {
                    "type": "string",
                    "enum": ["todo", "in_progress", "blocked", "done"],
                    "description": "Current task status. Defaults to 'todo'.",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "update_task",
        "description": (
            "Update an existing task's fields such as status, priority, due date, "
            "or description. Use this to mark tasks done, change priority, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "ID of the task to update."},
                "title": {"type": "string", "description": "New title (optional)."},
                "description": {"type": "string", "description": "New description (optional)."},
                "status": {
                    "type": "string",
                    "enum": ["todo", "in_progress", "blocked", "done"],
                    "description": "New status.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "New priority.",
                },
                "due_date": {"type": "string", "description": "New due date in ISO 8601 format."},
                "project_id": {"type": "integer", "description": "Reassign to a different project."},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "create_project",
        "description": (
            "Create a new project. Projects group related tasks and have deadlines "
            "and progress tracking."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project name."},
                "description": {"type": "string", "description": "Project description and goals."},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Project priority.",
                },
                "deadline": {"type": "string", "description": "Deadline in ISO 8601 format."},
                "status": {
                    "type": "string",
                    "enum": ["todo", "in_progress", "blocked", "done"],
                    "description": "Current project status.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "update_project",
        "description": "Update an existing project's fields.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "ID of the project to update."},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "status": {"type": "string", "enum": ["todo", "in_progress", "blocked", "done"]},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "deadline": {"type": "string", "description": "Deadline in ISO 8601 format."},
                "progress_pct": {"type": "number", "description": "Progress percentage 0-100."},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "create_lead",
        "description": (
            "Create a new CRM lead/contact. Use when Damarley mentions a new prospect, "
            "client, or networking contact."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Contact's full name."},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "company": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["new", "contacted", "qualified", "proposal", "won", "lost"],
                },
                "source": {"type": "string", "description": "Where the lead came from (email, instagram, referral, etc)."},
                "notes": {"type": "string"},
                "score": {"type": "number", "description": "Lead score 0-100 based on potential value."},
                "next_followup": {"type": "string", "description": "Next follow-up date in ISO 8601 format."},
            },
            "required": ["name"],
        },
    },
    {
        "name": "update_lead",
        "description": "Update an existing lead's status, score, notes, or follow-up date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "integer", "description": "ID of the lead to update."},
                "name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "company": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["new", "contacted", "qualified", "proposal", "won", "lost"],
                },
                "score": {"type": "number"},
                "notes": {"type": "string"},
                "next_followup": {"type": "string", "description": "ISO 8601 datetime."},
                "last_contact": {"type": "string", "description": "ISO 8601 datetime."},
            },
            "required": ["lead_id"],
        },
    },
    {
        "name": "create_content",
        "description": (
            "Create a new content item in the pipeline (idea, draft, scheduled post). "
            "Supports all platforms: Instagram, TikTok, YouTube, Facebook, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Content title or working name."},
                "body": {"type": "string", "description": "Content body or script."},
                "platform": {
                    "type": "string",
                    "enum": ["gmail", "instagram", "facebook", "tiktok", "youtube", "whatsapp", "other"],
                },
                "status": {
                    "type": "string",
                    "enum": ["idea", "draft", "review", "scheduled", "published"],
                },
                "caption": {"type": "string", "description": "Social media caption."},
                "hashtags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of hashtags.",
                },
                "scheduled_at": {"type": "string", "description": "Scheduled publish time (ISO 8601)."},
            },
            "required": ["title"],
        },
    },
    {
        "name": "update_content",
        "description": "Update an existing content item's status, body, platform, scheduling, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content_id": {"type": "integer", "description": "ID of the content item to update."},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "platform": {
                    "type": "string",
                    "enum": ["gmail", "instagram", "facebook", "tiktok", "youtube", "whatsapp", "other"],
                },
                "status": {
                    "type": "string",
                    "enum": ["idea", "draft", "review", "scheduled", "published"],
                },
                "caption": {"type": "string"},
                "hashtags": {"type": "array", "items": {"type": "string"}},
                "scheduled_at": {"type": "string"},
            },
            "required": ["content_id"],
        },
    },
    {
        "name": "create_event",
        "description": "Create a calendar event.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Event title."},
                "description": {"type": "string"},
                "location": {"type": "string"},
                "start_time": {"type": "string", "description": "Start time in ISO 8601 format."},
                "end_time": {"type": "string", "description": "End time in ISO 8601 format."},
                "is_all_day": {"type": "boolean", "description": "Whether this is an all-day event."},
            },
            "required": ["title", "start_time", "end_time"],
        },
    },
    {
        "name": "create_note",
        "description": (
            "Create a note in the knowledge hub. Good for capturing research, "
            "strategy ideas, meeting notes, or general thoughts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Note title."},
                "content": {"type": "string", "description": "Note body content (supports markdown)."},
                "category": {
                    "type": "string",
                    "description": "Category: research, strategy, idea, meeting_notes, or custom.",
                },
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for organization."},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "create_campaign",
        "description": "Create a new marketing campaign.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Campaign name."},
                "platform": {
                    "type": "string",
                    "enum": ["gmail", "instagram", "facebook", "tiktok", "youtube", "whatsapp", "other"],
                },
                "campaign_type": {
                    "type": "string",
                    "description": "Type: outreach, content, ads, email.",
                },
                "status": {"type": "string", "description": "draft, active, paused, or completed."},
                "target_audience": {"type": "string"},
                "goals": {"type": "object", "description": "Target metrics as key-value pairs."},
                "budget": {"type": "number"},
                "start_date": {"type": "string", "description": "ISO 8601 datetime."},
                "end_date": {"type": "string", "description": "ISO 8601 datetime."},
            },
            "required": ["name"],
        },
    },
    {
        "name": "update_campaign",
        "description": "Update an existing marketing campaign.",
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "integer", "description": "ID of the campaign to update."},
                "name": {"type": "string"},
                "status": {"type": "string"},
                "target_audience": {"type": "string"},
                "goals": {"type": "object"},
                "budget": {"type": "number"},
                "spent": {"type": "number"},
                "current_metrics": {"type": "object"},
                "ai_optimizations": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["campaign_id"],
        },
    },
    {
        "name": "search_records",
        "description": (
            "Search across any database model. Useful for finding tasks, projects, "
            "leads, content, events, notes, metrics, communications, campaigns, or scenarios. "
            "You can filter by any field on the model."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "enum": [
                        "Task", "Project", "Lead", "ContentItem", "CalendarEvent",
                        "Note", "Metric", "HealthEntry", "Communication", "Campaign",
                        "Scenario", "ImportedContext",
                    ],
                    "description": "Which model/table to search.",
                },
                "filters": {
                    "type": "object",
                    "description": (
                        "Key-value pairs to filter by. Keys must match model column names. "
                        "Example: {\"status\": \"todo\", \"priority\": \"high\"}"
                    ),
                },
                "limit": {"type": "integer", "description": "Max results to return. Default 20."},
                "skip": {"type": "integer", "description": "Offset for pagination. Default 0."},
            },
            "required": ["model"],
        },
    },
    {
        "name": "get_next_steps",
        "description": (
            "Get a prioritized list of recommended next actions based on the current "
            "state of all projects, tasks, leads, content pipeline, and calendar. "
            "Call this to help Damarley decide what to focus on."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "focus_area": {
                    "type": "string",
                    "description": (
                        "Optional focus area: 'all', 'projects', 'content', 'crm', "
                        "'health', 'finance'. Defaults to 'all'."
                    ),
                },
            },
            "required": [],
        },
    },
    {
        "name": "request_internet",
        "description": (
            "Request internet access for an operation that requires external data. "
            "This creates an approval request that Damarley must approve before "
            "any external connection is made. Use this when you need to fetch live "
            "data, call an external API, or access a website."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "purpose": {"type": "string", "description": "What you want to do and why."},
                "url_or_service": {"type": "string", "description": "The URL or service name to connect to."},
                "data_sent_description": {"type": "string", "description": "What data will be sent (if any)."},
                "data_received_description": {"type": "string", "description": "What data you expect to receive."},
                "precautions": {"type": "string", "description": "Privacy/security precautions in place."},
            },
            "required": ["purpose", "url_or_service"],
        },
    },
    {
        "name": "create_metric",
        "description": (
            "Record a business metric or KPI. Use for tracking revenue, expenses, "
            "ad spend, conversion rates, or any numeric measurement."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Metric category: revenue, expense, ad_spend, kpi, conversion, engagement.",
                },
                "name": {"type": "string", "description": "Metric name (e.g., 'Monthly Revenue', 'Instagram Followers')."},
                "value": {"type": "number", "description": "Numeric value."},
                "unit": {"type": "string", "description": "Unit of measurement: USD, %, count, etc."},
                "source": {"type": "string", "description": "Data source: quickbooks, google_ads, manual, etc."},
                "period_start": {"type": "string", "description": "Period start date (ISO 8601)."},
                "period_end": {"type": "string", "description": "Period end date (ISO 8601)."},
            },
            "required": ["category", "name", "value"],
        },
    },
    {
        "name": "create_health_entry",
        "description": (
            "Log a health, fitness, sleep, or supplement entry. "
            "Use when Damarley mentions workouts, sleep, supplements, or nutrition."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Category: workout, sleep, supplement, nutrition, weight, vitals.",
                },
                "name": {"type": "string", "description": "Name of the entry (e.g., 'Bench Press', '8h Sleep', 'Vitamin D')."},
                "value": {"type": "number", "description": "Numeric value (reps, hours, mg, etc)."},
                "unit": {"type": "string", "description": "Unit: reps, hours, mg, lbs, kg, kcal, etc."},
                "notes": {"type": "string", "description": "Additional notes."},
                "recorded_at": {"type": "string", "description": "When it was recorded (ISO 8601). Defaults to now."},
            },
            "required": ["category", "name"],
        },
    },
    {
        "name": "run_agent",
        "description": (
            "Delegate a task to a specialized AI agent. Use this ONLY when the task "
            "requires deep domain expertise that you cannot handle directly. Agents run "
            "on-demand — they are NOT running in the background. Available agents:\n"
            "- inbox: triage_messages, summarize_message, suggest_response, flag_urgent, process_inbox\n"
            "- crm: score_lead, suggest_followup, analyze_pipeline, automate_outreach, classify_lead_source\n"
            "- content: draft_post, schedule_post, generate_caption, analyze_performance\n"
            "- project: generate_daily_agenda, detect_bottlenecks, prioritize_tasks\n"
            "- finance: generate_kpi_report, detect_anomalies, forecast_revenue\n"
            "- health: analyze_sleep, score_energy, generate_supplement_plan\n"
            "- market: scan_competitors, identify_trends, find_opportunities\n"
            "- scenario: run_simulation, evaluate_decision\n"
            "- automation: run_workflow, execute_outreach_sequence"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "enum": ["inbox", "crm", "content", "project", "finance", "health", "market", "scenario", "automation", "outreach"],
                    "description": "Which specialized agent to delegate to.",
                },
                "action": {
                    "type": "string",
                    "description": "The exact method name to call on the agent.",
                },
                "params": {
                    "type": "object",
                    "description": "Parameters to pass to the action (can be empty object {}).",
                },
            },
            "required": ["agent", "action"],
        },
    },
]


# ---------------------------------------------------------------------------
# Model name -> class mapping for search_records
# ---------------------------------------------------------------------------

MODEL_MAP: Dict[str, Any] = {
    "Task": Task,
    "Project": Project,
    "Lead": Lead,
    "ContentItem": ContentItem,
    "CalendarEvent": CalendarEvent,
    "Note": Note,
    "Metric": Metric,
    "HealthEntry": HealthEntry,
    "Communication": Communication,
    "Campaign": Campaign,
    "Scenario": Scenario,
    "ImportedContext": ImportedContext,
}


# ---------------------------------------------------------------------------
# Enum resolution helpers
# ---------------------------------------------------------------------------

ENUM_MAP = {
    "priority": UrgencyLevel,
    "urgency": UrgencyLevel,
    "status": {
        "Task": TaskStatus,
        "Project": TaskStatus,
        "ContentItem": ContentStatus,
        "Lead": LeadStatus,
    },
    "platform": Platform,
}


def _resolve_enum(field_name: str, value: str, model_name: str = "") -> Any:
    """Resolve a string value to the correct SQLAlchemy enum member."""
    if field_name in ("priority", "urgency"):
        try:
            return UrgencyLevel(value)
        except ValueError:
            return value
    if field_name == "platform":
        try:
            return Platform(value)
        except ValueError:
            return value
    if field_name == "status":
        status_map = ENUM_MAP.get("status", {})
        if isinstance(status_map, dict):
            enum_cls = status_map.get(model_name)
            if enum_cls:
                try:
                    return enum_cls(value)
                except ValueError:
                    return value
    return value


def _parse_datetime(value: str) -> Optional[datetime]:
    """Attempt to parse an ISO 8601 datetime string."""
    if not value:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    # Last resort: let Python figure it out
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _serialize_record(record: Any) -> Dict[str, Any]:
    """Convert an ORM record to a JSON-serializable dict."""
    if record is None:
        return {}
    result = {}
    for col in record.__table__.columns:
        val = getattr(record, col.name, None)
        if isinstance(val, datetime):
            result[col.name] = val.isoformat()
        elif isinstance(val, enum_base):
            result[col.name] = val.value
        else:
            result[col.name] = val
    return result


# We need the base enum class for serialization
import enum as enum_base_module
enum_base = enum_base_module.Enum


# ---------------------------------------------------------------------------
# SupervisorAI — the core brain
# ---------------------------------------------------------------------------

class SupervisorAI:
    """Omura's central AI supervisor — Damarley's personal COO.

    Orchestrates all aspects of life and business management by combining
    conversational AI (Claude) with structured database operations and
    delegation to specialized agents.

    Parameters
    ----------
    db : Session
        SQLAlchemy database session for all data operations.
    """

    AGENT_NAME = "supervisor"
    MODEL = "claude-sonnet-4-6"
    MAX_CONTEXT_MESSAGES = 50
    MAX_IMPORTED_CONTEXT_ITEMS = 30
    MAX_TOOL_ITERATIONS = 15

    def __init__(self, db: Session) -> None:
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.logger = OmuraLogger("supervisor_ai")
        self.logger.info("SupervisorAI initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, user_message: str) -> Dict[str, Any]:
        """Process a user message and return the AI's response.

        This is the main entry point. It:
        1. Saves the user message to chat history
        2. Builds system prompt with current state
        3. Loads conversation context and imported context
        4. Calls Claude in a tool-use loop until a final text response
        5. Saves the assistant response to chat history
        6. Returns the response with metadata

        Parameters
        ----------
        user_message : str
            The message from Damarley.

        Returns
        -------
        dict
            {
                "reply": str,           # The assistant's text response
                "actions_taken": list,   # Actions performed via tool calls
                "internet_requested": bool  # Whether internet access was requested
            }
        """
        start_time = time.time()
        actions_taken: List[Dict[str, Any]] = []
        internet_requested = False

        try:
            # Save user message to history
            self._save_chat_message("user", user_message)

            # Build the system prompt with current operational state
            system_prompt = self._build_system_prompt()

            # Load conversation history and imported context
            context = self._load_context()
            messages = context["messages"]

            # Append the current user message
            messages.append({"role": "user", "content": user_message})

            # Run the Claude tool-use loop
            iteration = 0
            final_reply = ""

            while iteration < self.MAX_TOOL_ITERATIONS:
                iteration += 1
                self.logger.info(
                    f"Claude API call — iteration {iteration}, "
                    f"messages: {len(messages)}"
                )

                response = self.client.messages.create(
                    model=self.MODEL,
                    max_tokens=4096,
                    system=system_prompt,
                    tools=SUPERVISOR_TOOLS,
                    messages=messages,
                )

                # Check if the response contains tool use blocks
                has_tool_use = any(
                    block.type == "tool_use" for block in response.content
                )

                if response.stop_reason == "end_turn" or not has_tool_use:
                    # Extract final text from the response
                    text_parts = []
                    for block in response.content:
                        if hasattr(block, "text"):
                            text_parts.append(block.text)
                    final_reply = "\n".join(text_parts)
                    break

                # Process tool calls
                # First, append the assistant's message (with tool_use blocks)
                assistant_content = []
                for block in response.content:
                    if block.type == "text":
                        assistant_content.append({
                            "type": "text",
                            "text": block.text,
                        })
                    elif block.type == "tool_use":
                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })

                messages.append({"role": "assistant", "content": assistant_content})

                # Execute each tool call and collect results
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        self.logger.info(
                            f"Executing tool: {block.name} "
                            f"with input: {json.dumps(block.input, default=str)[:500]}"
                        )

                        result = self._execute_single_tool(
                            block.name, block.input
                        )
                        actions_taken.append({
                            "tool": block.name,
                            "input": block.input,
                            "result": result,
                        })

                        if block.name == "request_internet":
                            internet_requested = True

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str),
                        })

                # Append tool results as a user message
                messages.append({"role": "user", "content": tool_results})

            else:
                # Exceeded max iterations
                final_reply = (
                    "I've been working through several steps and need to pause. "
                    "Here's what I've accomplished so far — let me know if you'd "
                    "like me to continue."
                )
                self.logger.warning(
                    f"Reached max tool iterations ({self.MAX_TOOL_ITERATIONS})"
                )

            # Save assistant response to chat history
            self._save_chat_message(
                "assistant",
                final_reply,
                agent_used=self.AGENT_NAME,
                actions_taken=actions_taken,
                internet_requested=internet_requested,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Log the interaction to the audit trail
            crud.log_agent_action(
                self.db,
                agent_name=self.AGENT_NAME,
                action="chat",
                input_data={"user_message": user_message[:500]},
                output_data={
                    "reply_length": len(final_reply),
                    "actions_count": len(actions_taken),
                    "internet_requested": internet_requested,
                    "iterations": iteration,
                },
                status="success",
                duration_ms=duration_ms,
            )

            self.logger.info(
                f"Chat complete — {len(actions_taken)} actions, "
                f"{duration_ms}ms, internet_requested={internet_requested}"
            )

            return {
                "reply": final_reply,
                "actions_taken": actions_taken,
                "internet_requested": internet_requested,
            }

        except anthropic.APIConnectionError as exc:
            self.logger.error(f"Anthropic API connection error: {exc}")
            return self._error_response(
                "I'm having trouble connecting to my AI backend. "
                "Please check the API key and network connection.",
                exc, user_message, start_time,
            )
        except anthropic.RateLimitError as exc:
            self.logger.error(f"Anthropic rate limit: {exc}")
            return self._error_response(
                "I've hit the API rate limit. Please try again in a moment.",
                exc, user_message, start_time,
            )
        except anthropic.APIStatusError as exc:
            self.logger.error(f"Anthropic API error {exc.status_code}: {exc}")
            return self._error_response(
                f"AI service returned an error (status {exc.status_code}). "
                "I'll keep working with what I have.",
                exc, user_message, start_time,
            )
        except Exception as exc:
            self.logger.error(f"Unexpected error in chat: {traceback.format_exc()}")
            return self._error_response(
                "Something unexpected went wrong. The error has been logged "
                "and I'll make sure it gets fixed.",
                exc, user_message, start_time,
            )

    # ------------------------------------------------------------------
    # System prompt construction
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        """Build the system prompt with current operational state.

        The prompt positions the AI as Damarley's personal COO / chief of
        staff, with full awareness of his current projects, tasks, leads,
        calendar, content pipeline, and health data.

        Returns
        -------
        str
            The complete system prompt.
        """
        state = self._get_current_state()
        imported_context = self._load_imported_context()

        today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")

        system_prompt = f"""You are Omura — Damarley's personal AI Chief Operating Officer and Chief of Staff.

You are the central brain of the Omura Life Manager platform. Your role is to proactively manage, organize, and optimize every aspect of Damarley's professional and personal life. You think strategically, act precisely, and always keep Damarley's best interests at the center of every decision.

## YOUR IDENTITY
- Name: Omura (the Supervisor AI)
- Role: Personal COO / Chief of Staff to Damarley
- Personality: Highly competent, direct but warm, proactive, and strategic. You anticipate needs before they arise.
- Communication style: Clear, concise, and action-oriented. Use bullet points for action items. Be conversational but efficient.

## TODAY
{today}

## CORE PRINCIPLES
1. **Protect Damarley's time** — His time is the most valuable resource. Prioritize ruthlessly.
2. **Default to action** — When you can resolve something with a tool call, do it rather than just suggesting it.
3. **Be transparent** — Always explain what you did and why. Never take significant actions without context.
4. **Internet safety** — You NEVER access the internet without explicit approval. When you need external data, use the request_internet tool to create an approval request.
5. **Context awareness** — Use imported context and chat history to understand Damarley's goals, preferences, and ongoing initiatives.

## YOUR CAPABILITIES
You can directly manage:
- **Tasks & Projects**: Create, update, prioritize, and track tasks and projects
- **CRM / Leads**: Manage contacts, track lead scores, set follow-up reminders
- **Content Pipeline**: Create content ideas, move them through the pipeline (idea → draft → review → scheduled → published)
- **Calendar**: Create events and manage scheduling
- **Knowledge Hub**: Create notes, research documents, and strategy docs
- **Marketing Campaigns**: Create and manage campaigns across platforms
- **Metrics & KPIs**: Track business metrics, revenue, expenses, and performance data
- **Health Tracking**: Log workouts, sleep, supplements, and nutrition
- **Search**: Query any data in the system

You can delegate to specialized agents via the `run_agent` tool (on-demand only — they do NOT run in the background):
- **inbox**: triage_messages, summarize_message, suggest_response, flag_urgent, process_inbox
- **crm**: score_lead, suggest_followup, analyze_pipeline, automate_outreach, classify_lead_source
- **content**: draft_post, schedule_post, generate_caption, analyze_performance
- **project**: generate_daily_agenda, detect_bottlenecks, prioritize_tasks
- **finance**: generate_kpi_report, detect_anomalies, forecast_revenue
- **health**: analyze_sleep, score_energy, generate_supplement_plan
- **market**: scan_competitors, identify_trends, find_opportunities
- **scenario**: run_simulation, evaluate_decision
- **automation**: run_workflow, execute_outreach_sequence

Use `run_agent` only when specialized analysis is genuinely needed — for routine CRUD and conversation, handle it directly with your own tools to conserve API credits.

## CURRENT OPERATIONAL STATE

### Tasks Due Today ({len(state.get('tasks_due_today', []))} items)
{self._format_tasks(state.get('tasks_due_today', []))}

### Overdue Tasks ({len(state.get('overdue_tasks', []))} items)
{self._format_tasks(state.get('overdue_tasks', []))}

### Active Projects ({len(state.get('active_projects', []))} projects)
{self._format_projects(state.get('active_projects', []))}

### Hot Leads ({len(state.get('hot_leads', []))} leads)
{self._format_leads(state.get('hot_leads', []))}

### Leads Needing Follow-up ({len(state.get('leads_needing_followup', []))} leads)
{self._format_leads(state.get('leads_needing_followup', []))}

### Today's Calendar ({len(state.get('todays_events', []))} events)
{self._format_events(state.get('todays_events', []))}

### Upcoming Events (Next 7 Days: {len(state.get('upcoming_events', []))} events)
{self._format_events(state.get('upcoming_events', []))}

### Content Pipeline ({len(state.get('content_pipeline', []))} items)
{self._format_content(state.get('content_pipeline', []))}

### Unread Communications ({len(state.get('unread_comms', []))} messages)
{self._format_communications(state.get('unread_comms', []))}

### Urgent Communications ({len(state.get('urgent_comms', []))} messages)
{self._format_communications(state.get('urgent_comms', []))}

### KPI Summary (Last 30 Days)
{self._format_kpis(state.get('kpi_summary', {}))}

### Recent Health Data (Last 7 Days)
{self._format_health(state.get('health_entries', []))}

## IMPORTED CONTEXT (Damarley's Goals, Preferences & Background)
{imported_context}

## RESPONSE GUIDELINES
- You are Jarvis. Talk like it. Sharp, direct, human. NO MARKDOWN HEADERS WHATSOEVER. Do not output `#`, `##`, or `###`.
- Simple questions or greetings: 1-2 sentences max. No formatting. No bold or italics.
- When Damarley says to do something — DO IT immediately using tools, then confirm in one short conversational line. Example: "Done — created the task and set it high priority."
- When presenting a list (tasks, leads, projects): use a plain numbered list (1, 2, 3), NO headers, NO bold labels. Never use `#`.
- Never say "I'll help you with that" or "Great question" or "Certainly". Just act.
- When you need internet data, use request_internet. Never fake live data.
- Chain tool calls to complete complex requests fully before responding. Summarize everything done in 1-2 lines after.
- You can create/update/delete tasks, projects, leads, content, events, notes, campaigns, metrics, health entries. Do it without being asked twice.
- If Damarley says something is wrong, fix it. If he says add something, add it. No clarifying questions unless truly ambiguous.
"""
        return system_prompt

    # ------------------------------------------------------------------
    # Context loading
    # ------------------------------------------------------------------

    def _load_context(self) -> Dict[str, Any]:
        """Load recent chat history to maintain conversation continuity.

        Returns
        -------
        dict
            {"messages": list} — formatted for the Claude messages API.
        """
        try:
            recent_messages = (
                self.db.query(ChatMessage)
                .order_by(desc(ChatMessage.created_at))
                .limit(self.MAX_CONTEXT_MESSAGES)
                .all()
            )
            # Reverse to chronological order
            recent_messages = list(reversed(recent_messages))
        except Exception as exc:
            self.logger.warning(f"Failed to load chat history: {exc}")
            recent_messages = []

        messages = []
        for msg in recent_messages:
            role = msg.role
            # Claude API only accepts "user" and "assistant" roles in messages
            if role not in ("user", "assistant"):
                continue
            messages.append({
                "role": role,
                "content": msg.content,
            })

        # Ensure messages alternate properly (Claude requires user/assistant alternation)
        messages = self._ensure_message_alternation(messages)

        return {"messages": messages}

    def _load_imported_context(self) -> str:
        """Load imported context from ChatGPT exports and other sources.

        This gives the AI deep knowledge of Damarley's goals, preferences,
        ongoing projects, and personal background.

        Returns
        -------
        str
            Formatted context string for inclusion in the system prompt.
        """
        try:
            contexts = (
                self.db.query(ImportedContext)
                .order_by(desc(ImportedContext.created_at))
                .limit(self.MAX_IMPORTED_CONTEXT_ITEMS)
                .all()
            )
        except Exception as exc:
            self.logger.warning(f"Failed to load imported context: {exc}")
            return "No imported context available yet."

        if not contexts:
            return "No imported context available yet. Consider importing ChatGPT conversation exports or adding context manually."

        sections: List[str] = []
        for ctx in contexts:
            category = ctx.category or "general"
            title = ctx.title or "Untitled"
            # Truncate very long context entries to keep prompt manageable
            content = ctx.content
            if len(content) > 2000:
                content = content[:2000] + "... [truncated]"
            tags = ", ".join(ctx.tags) if ctx.tags else ""
            tag_str = f" (tags: {tags})" if tags else ""
            sections.append(
                f"### [{category.upper()}] {title}{tag_str}\n"
                f"Source: {ctx.source} | Imported: {ctx.created_at.strftime('%Y-%m-%d') if ctx.created_at else 'unknown'}\n"
                f"{content}"
            )

        return "\n\n".join(sections)

    # ------------------------------------------------------------------
    # Current state snapshot
    # ------------------------------------------------------------------

    def _get_current_state(self) -> Dict[str, Any]:
        """Query the database for a comprehensive snapshot of current state.

        Returns
        -------
        dict
            All the key operational data needed for the system prompt.
        """
        state: Dict[str, Any] = {}

        queries = {
            "tasks_due_today": lambda: crud.get_tasks_due_today(self.db),
            "overdue_tasks": lambda: crud.get_overdue_tasks(self.db),
            "active_projects": lambda: crud.get_active_projects(self.db),
            "hot_leads": lambda: crud.get_hot_leads(self.db),
            "leads_needing_followup": lambda: crud.get_leads_needing_followup(self.db),
            "todays_events": lambda: crud.get_todays_events(self.db),
            "upcoming_events": lambda: crud.get_upcoming_events(self.db),
            "content_pipeline": lambda: crud.get_content_pipeline(self.db),
            "unread_comms": lambda: crud.get_unread_communications(self.db),
            "urgent_comms": lambda: crud.get_urgent_communications(self.db),
            "kpi_summary": lambda: crud.get_kpi_summary(self.db),
            "health_entries": lambda: crud.get_health_entries(self.db),
        }

        for key, query_fn in queries.items():
            try:
                state[key] = query_fn()
            except Exception as exc:
                self.logger.warning(f"Failed to load {key}: {exc}")
                state[key] = [] if key != "kpi_summary" else {}

        return state

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute a batch of tool calls and return results.

        Parameters
        ----------
        tool_calls : list
            List of dicts with 'name' and 'input' keys.

        Returns
        -------
        list
            List of result dicts.
        """
        results = []
        for call in tool_calls:
            result = self._execute_single_tool(call["name"], call["input"])
            results.append(result)
        return results

    def _execute_single_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool call and return the result.

        All tool executions are wrapped in error handling and logged to
        the AgentLog table.

        Parameters
        ----------
        tool_name : str
            The name of the tool to execute.
        tool_input : dict
            The input parameters for the tool.

        Returns
        -------
        dict
            Result of the tool execution.
        """
        start_time = time.time()
        try:
            result = self._dispatch_tool(tool_name, tool_input)
            duration_ms = int((time.time() - start_time) * 1000)

            crud.log_agent_action(
                self.db,
                agent_name=self.AGENT_NAME,
                action=f"tool:{tool_name}",
                input_data=tool_input,
                output_data=result,
                status="success",
                duration_ms=duration_ms,
            )

            return result

        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"{type(exc).__name__}: {exc}"
            self.logger.error(f"Tool {tool_name} failed: {error_msg}")

            crud.log_agent_action(
                self.db,
                agent_name=self.AGENT_NAME,
                action=f"tool:{tool_name}",
                input_data=tool_input,
                output_data=None,
                status="error",
                error_message=error_msg,
                duration_ms=duration_ms,
            )

            return {
                "success": False,
                "error": error_msg,
            }

    def _dispatch_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Route a tool call to the appropriate handler.

        Parameters
        ----------
        tool_name : str
            Tool name from the Claude response.
        params : dict
            Tool input parameters.

        Returns
        -------
        dict
            Tool execution result.
        """
        dispatch = {
            "create_task": self._tool_create_task,
            "update_task": self._tool_update_task,
            "create_project": self._tool_create_project,
            "update_project": self._tool_update_project,
            "create_lead": self._tool_create_lead,
            "update_lead": self._tool_update_lead,
            "create_content": self._tool_create_content,
            "update_content": self._tool_update_content,
            "create_event": self._tool_create_event,
            "create_note": self._tool_create_note,
            "create_campaign": self._tool_create_campaign,
            "update_campaign": self._tool_update_campaign,
            "search_records": self._tool_search_records,
            "get_next_steps": self._tool_get_next_steps,
            "request_internet": self._tool_request_internet,
            "create_metric": self._tool_create_metric,
            "create_health_entry": self._tool_create_health_entry,
            "run_agent": self._tool_run_agent,
        }

        handler = dispatch.get(tool_name)
        if not handler:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        return handler(params)

    # ------------------------------------------------------------------
    # Tool handlers — CRUD operations
    # ------------------------------------------------------------------

    def _tool_create_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {"title": params["title"]}
        if "description" in params:
            kwargs["description"] = params["description"]
        if "project_id" in params:
            kwargs["project_id"] = params["project_id"]
        if "priority" in params:
            kwargs["priority"] = _resolve_enum("priority", params["priority"])
        if "status" in params:
            kwargs["status"] = _resolve_enum("status", params["status"], "Task")
        if "due_date" in params:
            kwargs["due_date"] = _parse_datetime(params["due_date"])

        record = crud.create_record(self.db, Task, **kwargs)
        return {
            "success": True,
            "action": "created_task",
            "task": _serialize_record(record),
        }

    def _tool_update_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_id = params.pop("task_id")
        kwargs: Dict[str, Any] = {}
        for field in ("title", "description", "project_id"):
            if field in params:
                kwargs[field] = params[field]
        if "priority" in params:
            kwargs["priority"] = _resolve_enum("priority", params["priority"])
        if "status" in params:
            kwargs["status"] = _resolve_enum("status", params["status"], "Task")
        if "due_date" in params:
            kwargs["due_date"] = _parse_datetime(params["due_date"])

        record = crud.update_record(self.db, Task, task_id, **kwargs)
        if not record:
            return {"success": False, "error": f"Task {task_id} not found."}
        return {
            "success": True,
            "action": "updated_task",
            "task": _serialize_record(record),
        }

    def _tool_create_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {"name": params["name"]}
        if "description" in params:
            kwargs["description"] = params["description"]
        if "priority" in params:
            kwargs["priority"] = _resolve_enum("priority", params["priority"])
        if "status" in params:
            kwargs["status"] = _resolve_enum("status", params["status"], "Project")
        if "deadline" in params:
            kwargs["deadline"] = _parse_datetime(params["deadline"])

        record = crud.create_record(self.db, Project, **kwargs)
        return {
            "success": True,
            "action": "created_project",
            "project": _serialize_record(record),
        }

    def _tool_update_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        project_id = params.pop("project_id")
        kwargs: Dict[str, Any] = {}
        for field in ("name", "description", "progress_pct"):
            if field in params:
                kwargs[field] = params[field]
        if "priority" in params:
            kwargs["priority"] = _resolve_enum("priority", params["priority"])
        if "status" in params:
            kwargs["status"] = _resolve_enum("status", params["status"], "Project")
        if "deadline" in params:
            kwargs["deadline"] = _parse_datetime(params["deadline"])

        record = crud.update_record(self.db, Project, project_id, **kwargs)
        if not record:
            return {"success": False, "error": f"Project {project_id} not found."}
        return {
            "success": True,
            "action": "updated_project",
            "project": _serialize_record(record),
        }

    def _tool_create_lead(self, params: Dict[str, Any]) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {"name": params["name"]}
        for field in ("email", "phone", "company", "source", "notes"):
            if field in params:
                kwargs[field] = params[field]
        if "status" in params:
            kwargs["status"] = _resolve_enum("status", params["status"], "Lead")
        if "score" in params:
            kwargs["score"] = float(params["score"])
        if "next_followup" in params:
            kwargs["next_followup"] = _parse_datetime(params["next_followup"])

        record = crud.create_record(self.db, Lead, **kwargs)
        return {
            "success": True,
            "action": "created_lead",
            "lead": _serialize_record(record),
        }

    def _tool_update_lead(self, params: Dict[str, Any]) -> Dict[str, Any]:
        lead_id = params.pop("lead_id")
        kwargs: Dict[str, Any] = {}
        for field in ("name", "email", "phone", "company", "source", "notes"):
            if field in params:
                kwargs[field] = params[field]
        if "status" in params:
            kwargs["status"] = _resolve_enum("status", params["status"], "Lead")
        if "score" in params:
            kwargs["score"] = float(params["score"])
        if "next_followup" in params:
            kwargs["next_followup"] = _parse_datetime(params["next_followup"])
        if "last_contact" in params:
            kwargs["last_contact"] = _parse_datetime(params["last_contact"])

        record = crud.update_record(self.db, Lead, lead_id, **kwargs)
        if not record:
            return {"success": False, "error": f"Lead {lead_id} not found."}
        return {
            "success": True,
            "action": "updated_lead",
            "lead": _serialize_record(record),
        }

    def _tool_create_content(self, params: Dict[str, Any]) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {"title": params["title"]}
        for field in ("body", "caption"):
            if field in params:
                kwargs[field] = params[field]
        if "platform" in params:
            kwargs["platform"] = _resolve_enum("platform", params["platform"])
        if "status" in params:
            kwargs["status"] = _resolve_enum("status", params["status"], "ContentItem")
        if "hashtags" in params:
            kwargs["hashtags"] = params["hashtags"]
        if "scheduled_at" in params:
            kwargs["scheduled_at"] = _parse_datetime(params["scheduled_at"])

        record = crud.create_record(self.db, ContentItem, **kwargs)
        return {
            "success": True,
            "action": "created_content",
            "content": _serialize_record(record),
        }

    def _tool_update_content(self, params: Dict[str, Any]) -> Dict[str, Any]:
        content_id = params.pop("content_id")
        kwargs: Dict[str, Any] = {}
        for field in ("title", "body", "caption", "hashtags"):
            if field in params:
                kwargs[field] = params[field]
        if "platform" in params:
            kwargs["platform"] = _resolve_enum("platform", params["platform"])
        if "status" in params:
            kwargs["status"] = _resolve_enum("status", params["status"], "ContentItem")
        if "scheduled_at" in params:
            kwargs["scheduled_at"] = _parse_datetime(params["scheduled_at"])

        record = crud.update_record(self.db, ContentItem, content_id, **kwargs)
        if not record:
            return {"success": False, "error": f"Content item {content_id} not found."}
        return {
            "success": True,
            "action": "updated_content",
            "content": _serialize_record(record),
        }

    def _tool_create_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "title": params["title"],
            "start_time": _parse_datetime(params["start_time"]),
            "end_time": _parse_datetime(params["end_time"]),
            "source": "manual",
        }
        for field in ("description", "location"):
            if field in params:
                kwargs[field] = params[field]
        if "is_all_day" in params:
            kwargs["is_all_day"] = bool(params["is_all_day"])

        record = crud.create_record(self.db, CalendarEvent, **kwargs)
        return {
            "success": True,
            "action": "created_event",
            "event": _serialize_record(record),
        }

    def _tool_create_note(self, params: Dict[str, Any]) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "title": params["title"],
            "content": params["content"],
            "source": "supervisor_ai",
        }
        if "category" in params:
            kwargs["category"] = params["category"]
        if "tags" in params:
            kwargs["tags"] = params["tags"]

        record = crud.create_record(self.db, Note, **kwargs)
        return {
            "success": True,
            "action": "created_note",
            "note": _serialize_record(record),
        }

    def _tool_create_campaign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {"name": params["name"]}
        for field in ("campaign_type", "status", "target_audience", "goals", "budget"):
            if field in params:
                kwargs[field] = params[field]
        if "platform" in params:
            kwargs["platform"] = _resolve_enum("platform", params["platform"])
        if "start_date" in params:
            kwargs["start_date"] = _parse_datetime(params["start_date"])
        if "end_date" in params:
            kwargs["end_date"] = _parse_datetime(params["end_date"])

        record = crud.create_record(self.db, Campaign, **kwargs)
        return {
            "success": True,
            "action": "created_campaign",
            "campaign": _serialize_record(record),
        }

    def _tool_update_campaign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = params.pop("campaign_id")
        kwargs: Dict[str, Any] = {}
        for field in ("name", "status", "target_audience", "goals", "budget",
                       "spent", "current_metrics", "ai_optimizations"):
            if field in params:
                kwargs[field] = params[field]

        record = crud.update_record(self.db, Campaign, campaign_id, **kwargs)
        if not record:
            return {"success": False, "error": f"Campaign {campaign_id} not found."}
        return {
            "success": True,
            "action": "updated_campaign",
            "campaign": _serialize_record(record),
        }

    def _tool_search_records(self, params: Dict[str, Any]) -> Dict[str, Any]:
        model_name = params["model"]
        model_class = MODEL_MAP.get(model_name)
        if not model_class:
            return {
                "success": False,
                "error": f"Unknown model: {model_name}. Available: {list(MODEL_MAP.keys())}",
            }

        filters = params.get("filters", {})
        limit = params.get("limit", 20)
        skip = params.get("skip", 0)

        # Resolve enum values in filters
        resolved_filters = {}
        for key, value in filters.items():
            if key in ("status", "priority", "urgency", "platform") and isinstance(value, str):
                resolved_filters[key] = _resolve_enum(key, value, model_name)
            else:
                resolved_filters[key] = value

        records = crud.get_records(
            self.db, model_class,
            skip=skip, limit=limit,
            **resolved_filters,
        )

        return {
            "success": True,
            "model": model_name,
            "count": len(records),
            "records": [_serialize_record(r) for r in records],
        }

    def _tool_get_next_steps(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build a prioritized list of next actions across all domains."""
        focus = params.get("focus_area", "all")
        next_steps: List[Dict[str, Any]] = []

        try:
            # Overdue tasks — highest priority
            if focus in ("all", "projects"):
                overdue = crud.get_overdue_tasks(self.db)
                for task in overdue[:5]:
                    next_steps.append({
                        "priority": "critical",
                        "area": "tasks",
                        "action": f"OVERDUE: Complete task '{task.title}' (ID: {task.id})",
                        "due": task.due_date.isoformat() if task.due_date else None,
                    })

            # Tasks due today
            if focus in ("all", "projects"):
                today_tasks = crud.get_tasks_due_today(self.db)
                for task in today_tasks[:5]:
                    next_steps.append({
                        "priority": "high",
                        "area": "tasks",
                        "action": f"DUE TODAY: '{task.title}' (ID: {task.id})",
                        "due": task.due_date.isoformat() if task.due_date else None,
                    })

            # Leads needing follow-up
            if focus in ("all", "crm"):
                followup_leads = crud.get_leads_needing_followup(self.db)
                for lead in followup_leads[:5]:
                    next_steps.append({
                        "priority": "high",
                        "area": "crm",
                        "action": (
                            f"Follow up with {lead.name}"
                            f" ({lead.company or 'no company'})"
                            f" — score: {lead.score} (ID: {lead.id})"
                        ),
                        "due": lead.next_followup.isoformat() if lead.next_followup else None,
                    })

            # Urgent communications
            if focus in ("all",):
                urgent = crud.get_urgent_communications(self.db)
                for comm in urgent[:3]:
                    next_steps.append({
                        "priority": "high",
                        "area": "inbox",
                        "action": (
                            f"Respond to urgent message from {comm.sender}: "
                            f"'{comm.subject or '(no subject)'}' (ID: {comm.id})"
                        ),
                    })

            # Content in review or draft
            if focus in ("all", "content"):
                pipeline = crud.get_content_pipeline(self.db)
                for item in pipeline[:5]:
                    status_label = item.status.value if hasattr(item.status, 'value') else str(item.status)
                    next_steps.append({
                        "priority": "medium",
                        "area": "content",
                        "action": (
                            f"Content '{item.title}' is in '{status_label}' stage"
                            f" — move it forward (ID: {item.id})"
                        ),
                    })

            # Today's events as awareness items
            if focus in ("all",):
                events = crud.get_todays_events(self.db)
                for event in events:
                    next_steps.append({
                        "priority": "info",
                        "area": "calendar",
                        "action": (
                            f"Calendar: '{event.title}' at "
                            f"{event.start_time.strftime('%I:%M %p') if event.start_time else 'TBD'}"
                        ),
                    })

        except Exception as exc:
            self.logger.error(f"Error building next steps: {exc}")
            return {
                "success": False,
                "error": f"Failed to build next steps: {exc}",
            }

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        next_steps.sort(key=lambda s: priority_order.get(s.get("priority", "low"), 3))

        return {
            "success": True,
            "focus_area": focus,
            "total_items": len(next_steps),
            "next_steps": next_steps,
        }

    def _tool_request_internet(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create an internet access request for approval."""
        return self._request_internet_access(
            agent=self.AGENT_NAME,
            purpose=params["purpose"],
            url=params["url_or_service"],
            data_description=params.get("data_sent_description", ""),
            precautions=params.get("precautions", ""),
            data_received=params.get("data_received_description", ""),
        )

    def _tool_create_metric(self, params: Dict[str, Any]) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "category": params["category"],
            "name": params["name"],
            "value": float(params["value"]),
        }
        for field in ("unit", "source"):
            if field in params:
                kwargs[field] = params[field]
        if "period_start" in params:
            kwargs["period_start"] = _parse_datetime(params["period_start"])
        if "period_end" in params:
            kwargs["period_end"] = _parse_datetime(params["period_end"])

        record = crud.create_record(self.db, Metric, **kwargs)
        return {
            "success": True,
            "action": "created_metric",
            "metric": _serialize_record(record),
        }

    def _tool_create_health_entry(self, params: Dict[str, Any]) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "category": params["category"],
            "name": params["name"],
            "source": "manual",
        }
        for field in ("unit", "notes"):
            if field in params:
                kwargs[field] = params[field]
        if "value" in params:
            kwargs["value"] = float(params["value"])
        if "recorded_at" in params:
            kwargs["recorded_at"] = _parse_datetime(params["recorded_at"])

        record = crud.create_record(self.db, HealthEntry, **kwargs)
        return {
            "success": True,
            "action": "created_health_entry",
            "health_entry": _serialize_record(record),
        }

    def _tool_run_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate a task to a specialized AI agent on-demand."""
        agent_name = params.get("agent", "")
        action = params.get("action", "")
        agent_params = params.get("params", {})

        AGENT_MAP = {
            "inbox": "backend.app.ai_agents.inbox_ai.InboxAI",
            "crm": "backend.app.ai_agents.crm_ai.CrmAI",
            "content": "backend.app.ai_agents.content_ai.ContentAI",
            "project": "backend.app.ai_agents.project_ai.ProjectAI",
            "finance": "backend.app.ai_agents.finance_ai.FinanceAI",
            "health": "backend.app.ai_agents.health_ai.HealthAI",
            "market": "backend.app.ai_agents.market_ai.MarketAI",
            "scenario": "backend.app.ai_agents.scenario_ai.ScenarioAI",
            "automation": "backend.app.ai_agents.automation_ai.AutomationAI",
            "outreach": "backend.app.ai_agents.outreach_ai.OutreachAI",
        }

        if agent_name not in AGENT_MAP:
            return {"success": False, "error": f"Unknown agent '{agent_name}'. Available: {list(AGENT_MAP.keys())}"}

        try:
            module_path, class_name = AGENT_MAP[agent_name].rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            AgentClass = getattr(module, class_name)
            agent_instance = AgentClass(self.db)

            method = getattr(agent_instance, action, None)
            if method is None or action.startswith("_"):
                return {"success": False, "error": f"Unknown action '{action}' for agent '{agent_name}'"}

            self.logger.info(f"Supervisor delegating to {agent_name}.{action}", params=agent_params)
            result = method(**agent_params)
            crud.log_agent_action(self.db, agent_name, action, agent_params, result if isinstance(result, dict) else {"result": str(result)}, "success")
            return {"success": True, "agent": agent_name, "action": action, "result": result}
        except Exception as exc:
            self.logger.error(f"Agent delegation failed: {agent_name}.{action}", error=str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Internet access request
    # ------------------------------------------------------------------

    def _request_internet_access(
        self,
        agent: str,
        purpose: str,
        url: str,
        data_description: str = "",
        precautions: str = "",
        data_received: str = "",
    ) -> Dict[str, Any]:
        """Create an InternetRequest record that must be approved by Damarley.

        Parameters
        ----------
        agent : str
            Name of the agent requesting access.
        purpose : str
            Why the internet access is needed.
        url : str
            The URL or service to connect to.
        data_description : str
            What data will be sent.
        precautions : str
            Privacy/security measures in place.
        data_received : str
            What data is expected to be received.

        Returns
        -------
        dict
            The created request record and instructions.
        """
        record = crud.create_record(
            self.db,
            InternetRequest,
            agent_name=agent,
            purpose=purpose,
            url_or_service=url,
            data_sent_description=data_description or "No data will be sent.",
            data_received_description=data_received or "External data retrieval.",
            precautions=precautions or "Standard security protocols applied.",
            status="pending",
        )

        crud.log_agent_action(
            self.db,
            agent_name=self.AGENT_NAME,
            action="internet_request_created",
            input_data={
                "purpose": purpose,
                "url": url,
            },
            output_data={"request_id": record.id},
            status="pending_approval",
        )

        self.logger.info(
            f"Internet request created (ID: {record.id}) — "
            f"awaiting approval for: {url}"
        )

        return {
            "success": True,
            "action": "internet_request_created",
            "request_id": record.id,
            "status": "pending_approval",
            "message": (
                f"Internet access request #{record.id} has been created and is "
                f"awaiting your approval. Purpose: {purpose}"
            ),
        }

    # ------------------------------------------------------------------
    # Chat history management
    # ------------------------------------------------------------------

    def _save_chat_message(
        self,
        role: str,
        content: str,
        agent_used: Optional[str] = None,
        actions_taken: Optional[List[Dict[str, Any]]] = None,
        internet_requested: bool = False,
    ) -> None:
        """Save a message to the chat history table.

        Parameters
        ----------
        role : str
            "user", "assistant", or "system".
        content : str
            The message content.
        agent_used : str, optional
            Which agent handled this message.
        actions_taken : list, optional
            Actions performed during processing.
        internet_requested : bool
            Whether internet access was requested.
        """
        try:
            crud.create_record(
                self.db,
                ChatMessage,
                role=role,
                content=content,
                agent_used=agent_used,
                actions_taken=actions_taken or [],
                internet_requested=internet_requested,
            )
        except Exception as exc:
            self.logger.error(f"Failed to save chat message: {exc}")

    # ------------------------------------------------------------------
    # Formatting helpers (for system prompt state display)
    # ------------------------------------------------------------------

    @staticmethod
    def _format_tasks(tasks: List[Any]) -> str:
        if not tasks:
            return "None."
        lines = []
        for t in tasks[:10]:
            status = t.status.value if hasattr(t.status, 'value') else str(t.status)
            priority = t.priority.value if hasattr(t.priority, 'value') else str(t.priority)
            due = t.due_date.strftime("%Y-%m-%d %H:%M") if t.due_date else "no due date"
            project_info = f" (Project #{t.project_id})" if t.project_id else ""
            lines.append(
                f"  - [ID:{t.id}] [{status}] [{priority}] {t.title} — due: {due}{project_info}"
            )
        if len(tasks) > 10:
            lines.append(f"  ... and {len(tasks) - 10} more")
        return "\n".join(lines)

    @staticmethod
    def _format_projects(projects: List[Any]) -> str:
        if not projects:
            return "None."
        lines = []
        for p in projects[:10]:
            status = p.status.value if hasattr(p.status, 'value') else str(p.status)
            priority = p.priority.value if hasattr(p.priority, 'value') else str(p.priority)
            deadline = p.deadline.strftime("%Y-%m-%d") if p.deadline else "no deadline"
            lines.append(
                f"  - [ID:{p.id}] [{status}] [{priority}] {p.name} — "
                f"{p.progress_pct or 0:.0f}% complete — deadline: {deadline}"
            )
        if len(projects) > 10:
            lines.append(f"  ... and {len(projects) - 10} more")
        return "\n".join(lines)

    @staticmethod
    def _format_leads(leads: List[Any]) -> str:
        if not leads:
            return "None."
        lines = []
        for lead in leads[:10]:
            status = lead.status.value if hasattr(lead.status, 'value') else str(lead.status)
            followup = (
                lead.next_followup.strftime("%Y-%m-%d")
                if lead.next_followup else "not set"
            )
            lines.append(
                f"  - [ID:{lead.id}] [{status}] {lead.name}"
                f" ({lead.company or 'no company'}) — "
                f"score: {lead.score or 0:.0f} — next follow-up: {followup}"
            )
        if len(leads) > 10:
            lines.append(f"  ... and {len(leads) - 10} more")
        return "\n".join(lines)

    @staticmethod
    def _format_events(events: List[Any]) -> str:
        if not events:
            return "None."
        lines = []
        for e in events[:10]:
            time_str = (
                e.start_time.strftime("%I:%M %p")
                if e.start_time and not e.is_all_day
                else "All day"
            )
            location = f" @ {e.location}" if e.location else ""
            lines.append(
                f"  - [ID:{e.id}] {time_str} — {e.title}{location}"
            )
        if len(events) > 10:
            lines.append(f"  ... and {len(events) - 10} more")
        return "\n".join(lines)

    @staticmethod
    def _format_content(items: List[Any]) -> str:
        if not items:
            return "None."
        lines = []
        for c in items[:10]:
            status = c.status.value if hasattr(c.status, 'value') else str(c.status)
            platform = c.platform.value if hasattr(c.platform, 'value') else str(c.platform or "unset")
            scheduled = (
                c.scheduled_at.strftime("%Y-%m-%d %H:%M")
                if c.scheduled_at else "not scheduled"
            )
            lines.append(
                f"  - [ID:{c.id}] [{status}] [{platform}] {c.title} — {scheduled}"
            )
        if len(items) > 10:
            lines.append(f"  ... and {len(items) - 10} more")
        return "\n".join(lines)

    @staticmethod
    def _format_communications(comms: List[Any]) -> str:
        if not comms:
            return "None."
        lines = []
        for c in comms[:5]:
            platform = c.platform.value if hasattr(c.platform, 'value') else str(c.platform)
            urgency = c.urgency.value if hasattr(c.urgency, 'value') else str(c.urgency)
            lines.append(
                f"  - [ID:{c.id}] [{platform}] [{urgency}] "
                f"From: {c.sender or 'unknown'} — {c.subject or '(no subject)'}"
            )
        if len(comms) > 5:
            lines.append(f"  ... and {len(comms) - 5} more")
        return "\n".join(lines)

    @staticmethod
    def _format_kpis(kpi_summary: Dict[str, Any]) -> str:
        if not kpi_summary:
            return "No KPI data available yet."
        lines = []
        for key, data in list(kpi_summary.items())[:15]:
            avg = data["total"] / data["count"] if data["count"] > 0 else 0
            lines.append(
                f"  - {key}: total={data['total']:.2f}, "
                f"avg={avg:.2f} {data.get('unit', '')}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_health(entries: List[Any]) -> str:
        if not entries:
            return "No recent health data."
        lines = []
        for h in entries[:10]:
            recorded = (
                h.recorded_at.strftime("%Y-%m-%d")
                if h.recorded_at else "unknown"
            )
            value_str = f"{h.value} {h.unit}" if h.value is not None else ""
            lines.append(
                f"  - [{recorded}] [{h.category}] {h.name} {value_str}"
            )
        if len(entries) > 10:
            lines.append(f"  ... and {len(entries) - 10} more")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_message_alternation(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure messages strictly alternate between user and assistant.

        The Claude API requires that messages alternate roles. This method
        removes any consecutive same-role messages by keeping the last one
        in each consecutive group.

        Parameters
        ----------
        messages : list
            List of message dicts with 'role' and 'content'.

        Returns
        -------
        list
            Cleaned message list with proper alternation.
        """
        if not messages:
            return []

        cleaned: List[Dict[str, Any]] = []
        for msg in messages:
            if cleaned and cleaned[-1]["role"] == msg["role"]:
                # Merge consecutive same-role messages
                existing = cleaned[-1]["content"]
                new_content = msg["content"]
                if isinstance(existing, str) and isinstance(new_content, str):
                    cleaned[-1]["content"] = existing + "\n\n" + new_content
                else:
                    # Replace with the newer message if content types differ
                    cleaned[-1] = msg
            else:
                cleaned.append(msg)

        # Claude requires the first message to be from the user
        if cleaned and cleaned[0]["role"] != "user":
            cleaned = cleaned[1:]

        return cleaned

    def _error_response(
        self,
        user_message: str,
        exc: Exception,
        original_input: str,
        start_time: float,
    ) -> Dict[str, Any]:
        """Build a standardized error response and log it.

        Parameters
        ----------
        user_message : str
            The friendly error message to show the user.
        exc : Exception
            The original exception.
        original_input : str
            The user's input that triggered the error.
        start_time : float
            When processing started (for duration calculation).

        Returns
        -------
        dict
            Standard response dict with error information.
        """
        duration_ms = int((time.time() - start_time) * 1000)

        crud.log_agent_action(
            self.db,
            agent_name=self.AGENT_NAME,
            action="chat",
            input_data={"user_message": original_input[:500]},
            output_data=None,
            status="error",
            error_message=f"{type(exc).__name__}: {exc}",
            duration_ms=duration_ms,
        )

        return {
            "reply": user_message,
            "actions_taken": [],
            "internet_requested": False,
        }
