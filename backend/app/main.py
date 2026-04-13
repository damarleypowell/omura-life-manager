"""
Omura Life Manager — FastAPI Entry Point
Main application with all API routes for the dashboard, AI agents, and integrations.
"""

import os as _os
from dotenv import load_dotenv as _load_dotenv
_load_dotenv(dotenv_path=_os.path.normpath(
    _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".env")
), override=True)

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
import httpx as _httpx
import base64 as _base64
import email as _email_lib
import queue as _queue
import threading as _threading
import json as _json
import re as _re
from html.parser import HTMLParser as _HTMLParser


class _HtmlStripper(_HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip = False  # True while inside <style> or <script>

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self):
        return _re.sub(r'\s+', ' ', ''.join(self._parts)).strip()


def _strip_html(html: str) -> str:
    if not html:
        return ''
    try:
        s = _HtmlStripper()
        s.feed(html)
        return s.get_text()
    except Exception:
        # Fallback: strip style/script blocks then tags
        html = _re.sub(r'<(style|script)[^>]*>.*?</(style|script)>', ' ', html, flags=_re.DOTALL | _re.IGNORECASE)
        return _re.sub(r'\s+', ' ', _re.sub(r'<[^>]+>', ' ', html)).strip()


def _extract_email_body(payload: dict) -> str:
    """Recursively extract plain text from a Gmail message payload.

    Prefers text/plain; falls back to text/html stripped of tags.
    Handles nested multipart/alternative, multipart/mixed, etc.
    """
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == "text/plain" and body_data:
        return _base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")

    if mime_type == "text/html" and body_data:
        raw = _base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")
        return _strip_html(raw)

    parts = payload.get("parts", [])
    # For multipart, try plain first then html
    plain = ""
    html_fallback = ""
    for part in parts:
        result = _extract_email_body(part)
        if part.get("mimeType", "").startswith("text/plain") and not plain:
            plain = result
        elif part.get("mimeType", "").startswith("text/html") and not html_fallback:
            html_fallback = result
        elif not plain and result:
            plain = result  # nested multipart that returned text

    return plain or html_fallback

from backend.app.config import settings
from backend.app.database.session import get_db, engine, Base
from backend.app.database import crud, models

# ── Create tables ──
Base.metadata.create_all(bind=engine)

# ── Runtime migrations (add columns that may not exist in older DBs) ──
from sqlalchemy import text as _sql_text, inspect as _inspect

def _run_migrations():
    inspector = _inspect(engine)
    # Add conversation_id to chat_messages if missing
    if 'chat_messages' in inspector.get_table_names():
        existing_cols = [c['name'] for c in inspector.get_columns('chat_messages')]
        if 'conversation_id' not in existing_cols:
            with engine.connect() as conn:
                conn.execute(_sql_text(
                    "ALTER TABLE chat_messages ADD COLUMN conversation_id INTEGER "
                    "REFERENCES conversations(id) ON DELETE SET NULL"
                ))
                conn.commit()

try:
    _run_migrations()
except Exception as _mig_err:
    print(f"WARNING: Migration check failed: {_mig_err} — continuing startup")

# ── Rate Limiting ──
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# ── App ──
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Personal & Business Operating System for Sir",
    docs_url="/docs",
    redoc_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://localhost:3001", "http://localhost:3002",
        "https://omura-life-manager.vercel.app",
        "https://omura-life-manager-damarleypowells-projects.vercel.app",
    ],
    allow_origin_regex=r"https://omura-life-manager.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Cache-Control", "X-Requested-With"],
)

# ── Security Headers Middleware ──
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)


# ══════════════════════════════════════════════
# Scheduled Automation (APScheduler)
# ══════════════════════════════════════════════

from backend.app.scheduler import scheduler as _scheduler, schedule_lead_followup_sequence
from backend.app.scheduler_jobs import scheduled_inbox_triage as _scheduled_inbox_triage
from backend.app.scheduler_jobs import scheduled_daily_briefing as _scheduled_daily_briefing
from backend.app.scheduler_jobs import scheduled_weekly_pipeline as _scheduled_weekly_pipeline
from backend.app.scheduler_jobs import scheduled_daily_outreach as _scheduled_daily_outreach

from backend.app.email_utils import send_via_sendgrid as _send_via_sendgrid
from backend.app.google_utils import get_google_access_token as _get_google_access_token, extract_email_body as _extract_email_body
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

_scheduler.add_job(_scheduled_inbox_triage, IntervalTrigger(minutes=30), id="inbox_triage", replace_existing=True)
_scheduler.add_job(_scheduled_daily_briefing, CronTrigger(hour=8, minute=0), id="daily_briefing", replace_existing=True)
_scheduler.add_job(_scheduled_weekly_pipeline, CronTrigger(day_of_week="mon", hour=9, minute=0), id="weekly_pipeline", replace_existing=True)
_scheduler.add_job(_scheduled_daily_outreach, CronTrigger(hour=9, minute=0), id="daily_outreach", replace_existing=True)

_scheduler.start()


# ══════════════════════════════════════════════
# Request / Response Schemas
# ══════════════════════════════════════════════

class CommunicationCreate(BaseModel):
    platform: str
    sender: str
    recipient: Optional[str] = None
    subject: Optional[str] = None
    body: str
    labels: Optional[list] = []

class CommunicationUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_flagged: Optional[bool] = None
    urgency: Optional[str] = None
    labels: Optional[list] = None

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[str] = "medium"

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    deadline: Optional[datetime] = None
    progress_pct: Optional[float] = None

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    project_id: Optional[int] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = "medium"

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None

class ContentCreate(BaseModel):
    title: str
    body: Optional[str] = None
    platform: str
    caption: Optional[str] = None
    hashtags: Optional[list] = []
    scheduled_at: Optional[datetime] = None

class ContentUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[list] = None
    scheduled_at: Optional[datetime] = None

class LeadCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None

class LeadUpdate(BaseModel):
    status: Optional[str] = None
    score: Optional[float] = None
    notes: Optional[str] = None
    next_followup: Optional[datetime] = None
    last_contact: Optional[datetime] = None

class MetricCreate(BaseModel):
    category: str
    name: str
    value: float
    unit: Optional[str] = None
    source: Optional[str] = None

class HealthEntryCreate(BaseModel):
    category: str
    name: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    notes: Optional[str] = None
    recorded_at: Optional[datetime] = None

class NoteCreate(BaseModel):
    title: str
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list] = []

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list] = None

class ScenarioCreate(BaseModel):
    name: str
    category: str
    parameters: dict

class SettingsUpdate(BaseModel):
    profile: Optional[dict] = None
    notifications: Optional[dict] = None
    agent_settings: Optional[dict] = None

class AIAgentRequest(BaseModel):
    agent: str
    action: str
    params: Optional[dict] = {}

class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"

class ConversationChatRequest(BaseModel):
    message: str

class WorkflowRequest(BaseModel):
    workflow: str
    params: Optional[dict] = {}


# ══════════════════════════════════════════════
# Health Check
# ══════════════════════════════════════════════

@app.get("/")
def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ══════════════════════════════════════════════
# Communications (Unified Inbox)
# ══════════════════════════════════════════════

@app.get("/api/communications")
def list_communications(
    platform: Optional[str] = None,
    is_read: Optional[bool] = None,
    skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db)
):
    filters = {}
    if platform:
        filters["platform"] = platform
    if is_read is not None:
        filters["is_read"] = is_read
    return crud.get_records(db, models.Communication, skip=skip, limit=limit, **filters)

@app.get("/api/communications/unread")
def unread_communications(platform: Optional[str] = None, db: Session = Depends(get_db)):
    return crud.get_unread_communications(db, platform)

@app.get("/api/communications/flagged")
def flagged_communications(db: Session = Depends(get_db)):
    return crud.get_flagged_communications(db)

@app.get("/api/communications/urgent")
def urgent_communications(db: Session = Depends(get_db)):
    return crud.get_urgent_communications(db)

@app.get("/api/communications/{comm_id}")
def get_communication(comm_id: int, db: Session = Depends(get_db)):
    record = crud.get_record(db, models.Communication, comm_id)
    if not record:
        raise HTTPException(404, "Communication not found")
    return record

@app.post("/api/communications")
def create_communication(data: CommunicationCreate, db: Session = Depends(get_db)):
    return crud.create_record(db, models.Communication, **data.model_dump())

@app.patch("/api/communications/{comm_id}")
def update_communication(comm_id: int, data: CommunicationUpdate, db: Session = Depends(get_db)):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    record = crud.update_record(db, models.Communication, comm_id, **updates)
    if not record:
        raise HTTPException(404, "Communication not found")
    return record


# ══════════════════════════════════════════════
# Projects
# ══════════════════════════════════════════════

@app.get("/api/projects")
def list_projects(status: Optional[str] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    filters = {}
    if status:
        filters["status"] = status
    return crud.get_records(db, models.Project, skip=skip, limit=limit, **filters)

@app.get("/api/projects/active")
def active_projects(db: Session = Depends(get_db)):
    return crud.get_active_projects(db)

@app.get("/api/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    record = crud.get_record(db, models.Project, project_id)
    if not record:
        raise HTTPException(404, "Project not found")
    return record

@app.post("/api/projects")
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    return crud.create_record(db, models.Project, **data.model_dump())

@app.patch("/api/projects/{project_id}")
def update_project(project_id: int, data: ProjectUpdate, db: Session = Depends(get_db)):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    record = crud.update_record(db, models.Project, project_id, **updates)
    if not record:
        raise HTTPException(404, "Project not found")
    return record

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    if not crud.delete_record(db, models.Project, project_id):
        raise HTTPException(404, "Project not found")
    return {"deleted": True}


# ══════════════════════════════════════════════
# Tasks
# ══════════════════════════════════════════════

@app.get("/api/tasks")
def list_tasks(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db)
):
    filters = {}
    if project_id:
        filters["project_id"] = project_id
    if status:
        filters["status"] = status
    return crud.get_records(db, models.Task, skip=skip, limit=limit, **filters)

@app.get("/api/tasks/today")
def tasks_today(db: Session = Depends(get_db)):
    return crud.get_tasks_due_today(db)

@app.get("/api/tasks/overdue")
def overdue_tasks(db: Session = Depends(get_db)):
    return crud.get_overdue_tasks(db)

@app.post("/api/tasks")
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    return crud.create_record(db, models.Task, **data.model_dump())

@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    record = crud.update_record(db, models.Task, task_id, **updates)
    if not record:
        raise HTTPException(404, "Task not found")
    return record

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    if not crud.delete_record(db, models.Task, task_id):
        raise HTTPException(404, "Task not found")
    return {"deleted": True}


# ══════════════════════════════════════════════
# Content Items
# ══════════════════════════════════════════════

@app.get("/api/content")
def list_content(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db)
):
    filters = {}
    if platform:
        filters["platform"] = platform
    if status:
        filters["status"] = status
    return crud.get_records(db, models.ContentItem, skip=skip, limit=limit, **filters)

@app.get("/api/content/pipeline")
def content_pipeline(db: Session = Depends(get_db)):
    return crud.get_content_pipeline(db)

@app.get("/api/content/scheduled")
def scheduled_content(platform: Optional[str] = None, db: Session = Depends(get_db)):
    return crud.get_scheduled_content(db, platform)

@app.post("/api/content")
def create_content(data: ContentCreate, db: Session = Depends(get_db)):
    return crud.create_record(db, models.ContentItem, **data.model_dump())

@app.patch("/api/content/{content_id}")
def update_content(content_id: int, data: ContentUpdate, db: Session = Depends(get_db)):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    record = crud.update_record(db, models.ContentItem, content_id, **updates)
    if not record:
        raise HTTPException(404, "Content not found")
    return record

@app.delete("/api/content/{content_id}")
def delete_content(content_id: int, db: Session = Depends(get_db)):
    if not crud.delete_record(db, models.ContentItem, content_id):
        raise HTTPException(404, "Content not found")
    return {"deleted": True}


# ══════════════════════════════════════════════
# CRM / Leads
# ══════════════════════════════════════════════

@app.get("/api/leads")
def list_leads(status: Optional[str] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    filters = {}
    if status:
        filters["status"] = status
    return crud.get_records(db, models.Lead, skip=skip, limit=limit, **filters)

@app.get("/api/leads/hot")
def hot_leads(min_score: float = 70.0, db: Session = Depends(get_db)):
    return crud.get_hot_leads(db, min_score)

@app.get("/api/leads/followups")
def leads_needing_followup(db: Session = Depends(get_db)):
    return crud.get_leads_needing_followup(db)

@app.post("/api/leads")
def create_lead(data: LeadCreate, db: Session = Depends(get_db)):
    lead = crud.create_record(db, models.Lead, **data.model_dump())
    # Auto-queue follow-up sequence for new leads with an email
    if getattr(lead, "email", None):
        schedule_lead_followup_sequence(lead.id)
    return lead

@app.patch("/api/leads/{lead_id}")
def update_lead(lead_id: int, data: LeadUpdate, db: Session = Depends(get_db)):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    record = crud.update_record(db, models.Lead, lead_id, **updates)
    if not record:
        raise HTTPException(404, "Lead not found")
    return record


# ══════════════════════════════════════════════
# Metrics / KPIs
# ══════════════════════════════════════════════

@app.get("/api/metrics")
def list_metrics(category: Optional[str] = None, days: int = 30, db: Session = Depends(get_db)):
    if category:
        return crud.get_metrics_by_category(db, category, days)
    return crud.get_records(db, models.Metric, limit=100)

@app.get("/api/metrics/kpis")
def kpi_summary(days: int = 30, db: Session = Depends(get_db)):
    return crud.get_kpi_summary(db, days)

@app.post("/api/metrics")
def create_metric(data: MetricCreate, db: Session = Depends(get_db)):
    return crud.create_record(db, models.Metric, **data.model_dump())


# ══════════════════════════════════════════════
# Health Entries
# ══════════════════════════════════════════════

@app.get("/api/health")
def list_health(category: Optional[str] = None, days: int = 7, db: Session = Depends(get_db)):
    return crud.get_health_entries(db, category, days)

@app.post("/api/health")
def create_health_entry(data: HealthEntryCreate, db: Session = Depends(get_db)):
    return crud.create_record(db, models.HealthEntry, **data.model_dump())


# ══════════════════════════════════════════════
# Calendar Events
# ══════════════════════════════════════════════

@app.get("/api/calendar")
def list_events(days: int = 7, db: Session = Depends(get_db)):
    return crud.get_upcoming_events(db, days)

@app.get("/api/calendar/today")
def todays_events(db: Session = Depends(get_db)):
    return crud.get_todays_events(db)

@app.post("/api/calendar")
def create_event(data: dict, db: Session = Depends(get_db)):
    return crud.create_record(db, models.CalendarEvent, **data)


# ══════════════════════════════════════════════
# Notes / Knowledge Hub
# ══════════════════════════════════════════════

@app.get("/api/notes")
def list_notes(category: Optional[str] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    filters = {}
    if category:
        filters["category"] = category
    return crud.get_records(db, models.Note, skip=skip, limit=limit, **filters)

@app.post("/api/notes")
def create_note(data: NoteCreate, db: Session = Depends(get_db)):
    return crud.create_record(db, models.Note, **data.model_dump())

@app.patch("/api/notes/{note_id}")
def update_note(note_id: int, data: NoteUpdate, db: Session = Depends(get_db)):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    record = crud.update_record(db, models.Note, note_id, **updates)
    if not record:
        raise HTTPException(404, "Note not found")
    return record

@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db)):
    if not crud.delete_record(db, models.Note, note_id):
        raise HTTPException(404, "Note not found")
    return {"deleted": True}


# ══════════════════════════════════════════════
# Scenarios (What-If Simulations)
# ══════════════════════════════════════════════

@app.get("/api/scenarios")
def list_scenarios(category: Optional[str] = None, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    filters = {}
    if category:
        filters["category"] = category
    return crud.get_records(db, models.Scenario, skip=skip, limit=limit, **filters)

@app.post("/api/scenarios")
def create_scenario(data: ScenarioCreate, db: Session = Depends(get_db)):
    return crud.create_record(db, models.Scenario, **data.model_dump())

@app.get("/api/scenarios/{scenario_id}")
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    record = crud.get_record(db, models.Scenario, scenario_id)
    if not record:
        raise HTTPException(404, "Scenario not found")
    return record


# ══════════════════════════════════════════════
# AI Agent Endpoints
# ══════════════════════════════════════════════

@app.post("/api/ai/execute")
def execute_ai_agent(request: AIAgentRequest, db: Session = Depends(get_db)):
    """Execute an AI agent action. Agents: inbox, content, project, crm, finance, health, market, scenario, automation."""
    from backend.app.ai_agents.inbox_ai import InboxAI
    from backend.app.ai_agents.content_ai import ContentAI
    from backend.app.ai_agents.project_ai import ProjectAI
    from backend.app.ai_agents.crm_ai import CrmAI
    from backend.app.ai_agents.finance_ai import FinanceAI
    from backend.app.ai_agents.health_ai import HealthAI
    from backend.app.ai_agents.market_ai import MarketAI
    from backend.app.ai_agents.scenario_ai import ScenarioAI
    from backend.app.ai_agents.automation_ai import AutomationAI
    from backend.app.ai_agents.outreach_ai import OutreachAI

    agents = {
        "inbox": InboxAI,
        "content": ContentAI,
        "project": ProjectAI,
        "crm": CrmAI,
        "finance": FinanceAI,
        "health": HealthAI,
        "market": MarketAI,
        "scenario": ScenarioAI,
        "automation": AutomationAI,
        "outreach": OutreachAI,
    }

    if request.agent not in agents:
        raise HTTPException(400, f"Unknown agent: {request.agent}. Available: {list(agents.keys())}")

    agent_instance = agents[request.agent](db)
    method = getattr(agent_instance, request.action, None)
    if not method or request.action.startswith("_"):
        raise HTTPException(400, f"Unknown action '{request.action}' for agent '{request.agent}'")

    try:
        result = method(**request.params)
        crud.log_agent_action(db, request.agent, request.action, request.params, result, "success")
        return {"agent": request.agent, "action": request.action, "result": result}
    except Exception as e:
        crud.log_agent_action(db, request.agent, request.action, request.params, None, "error", str(e))
        raise HTTPException(500, f"Agent error: {str(e)}")


@app.post("/api/ai/workflow")
def run_workflow(request: WorkflowRequest, db: Session = Depends(get_db)):
    """Run a named automation workflow."""
    from backend.app.ai_agents.automation_ai import AutomationAI
    automation = AutomationAI(db)
    try:
        result = automation.run_workflow(request.workflow, request.params)
        return {"workflow": request.workflow, "result": result}
    except Exception as e:
        raise HTTPException(500, f"Workflow error: {str(e)}")


# ══════════════════════════════════════════════
# Agent Logs
# ══════════════════════════════════════════════

@app.get("/api/agent-logs")
def list_agent_logs(agent_name: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_agent_logs(db, agent_name, limit)


@app.get("/api/scheduler/jobs")
def list_scheduler_jobs():
    """List all scheduled automation jobs and their next run times."""
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return {"jobs": jobs, "scheduler_running": _scheduler.running}


@app.post("/api/scheduler/trigger/{job_id}")
def trigger_job(job_id: str):
    """Manually trigger a scheduled job immediately."""
    valid_jobs = {
        "inbox_triage": _scheduled_inbox_triage,
        "daily_briefing": _scheduled_daily_briefing,
        "weekly_pipeline": _scheduled_weekly_pipeline,
    }
    if job_id not in valid_jobs:
        raise HTTPException(400, f"Unknown job: {job_id}. Valid: {list(valid_jobs.keys())}")
    import threading
    t = threading.Thread(target=valid_jobs[job_id], daemon=True)
    t.start()
    return {"status": "triggered", "job_id": job_id}


# ══════════════════════════════════════════════
# Dashboard Aggregation Endpoints
# ══════════════════════════════════════════════

@app.get("/api/dashboard/life-overview")
def life_overview(db: Session = Depends(get_db)):
    """Aggregated data for the Life Overview dashboard section."""
    return {
        "todays_events": crud.get_todays_events(db),
        "tasks_today": crud.get_tasks_due_today(db),
        "overdue_tasks": crud.get_overdue_tasks(db),
        "health_entries": crud.get_health_entries(db, days=1),
        "generated_at": datetime.utcnow().isoformat(),
    }

@app.get("/api/dashboard/business-command")
def business_command(db: Session = Depends(get_db)):
    """Aggregated data for the Business Command dashboard section."""
    return {
        "active_projects": crud.get_active_projects(db),
        "kpis": crud.get_kpi_summary(db),
        "hot_leads": crud.get_hot_leads(db),
        "recent_agent_logs": crud.get_agent_logs(db, limit=10),
        "generated_at": datetime.utcnow().isoformat(),
    }

@app.get("/api/dashboard/content-studio")
def content_studio(db: Session = Depends(get_db)):
    """Aggregated data for the Content Studio dashboard section."""
    return {
        "pipeline": crud.get_content_pipeline(db),
        "scheduled": crud.get_scheduled_content(db),
        "generated_at": datetime.utcnow().isoformat(),
    }

@app.get("/api/dashboard/communication-center")
def communication_center(db: Session = Depends(get_db)):
    """Aggregated data for the Communication Center dashboard section."""
    return {
        "unread": crud.get_unread_communications(db),
        "flagged": crud.get_flagged_communications(db),
        "urgent": crud.get_urgent_communications(db),
        "generated_at": datetime.utcnow().isoformat(),
    }


# ══════════════════════════════════════════════
# Email Sending — Gmail SMTP
# ══════════════════════════════════════════════

@app.post("/api/email/send")
def send_email(request: SendEmailRequest, db: Session = Depends(get_db)):
    """Send an email via Gmail SMTP."""
    from backend.app.email_utils import send_via_sendgrid as _gmail_send
    try:
        result = _gmail_send(
            to=request.to,
            subject=request.subject,
            body=request.body,
            cc=request.cc,
        )
        crud.log_agent_action(db, "system", "send_email",
            input_data={"to": request.to, "subject": request.subject, "provider": "gmail"},
            status="success")
        return result
    except Exception as e:
        crud.log_agent_action(db, "system", "send_email", status="error", error_message=str(e))
        raise HTTPException(500, f"Email send failed: {str(e)}")


@app.post("/api/email/test")
def test_email(db: Session = Depends(get_db)):
    """Quick test — sends a test email to the configured Gmail account itself."""
    from backend.app.email_utils import send_via_sendgrid as _gmail_send
    try:
        gmail_user = settings.GMAIL_USER
        result = _gmail_send(
            to=gmail_user,
            subject="Omura Email Test",
            body=f"Gmail SMTP is working. Sent at {datetime.utcnow().isoformat()}",
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"Test email failed: {str(e)}")


# ══════════════════════════════════════════════
# Google Sheets — Lead Pipeline Sync
# ══════════════════════════════════════════════

class SheetsImportRequest(BaseModel):
    sheet_url: str
    sheet_tab: Optional[str] = "Sheet1"

@app.post("/api/sheets/export")
def sheets_export_pipeline(db: Session = Depends(get_db)):
    """Export all leads to the Omura Lead Pipeline Google Sheet.
    Creates the sheet automatically if it doesn't exist yet.
    Returns the sheet URL.
    """
    from backend.app.google_sheets import export_pipeline_to_sheets
    from backend.app.google_utils import get_google_access_token
    access_token = get_google_access_token()
    if not access_token:
        raise HTTPException(401, "Google not connected. Go to /auth/google first.")
    try:
        result = export_pipeline_to_sheets(db, access_token)
        crud.log_agent_action(db, "system", "sheets_export", {},
            {"leads": result["leads_exported"], "url": result["sheet_url"]}, "success")
        return result
    except Exception as e:
        raise HTTPException(500, f"Sheets export failed: {str(e)}")


@app.post("/api/sheets/import")
def sheets_import_leads(request: SheetsImportRequest, db: Session = Depends(get_db)):
    """Import leads from a Google Sheet into the outreach pipeline.
    The sheet must have a header row with at minimum an 'Email' column.
    Paste the Google Sheets URL. Supports any column order.
    """
    from backend.app.google_sheets import import_leads_from_sheet, extract_sheet_id_from_url
    from backend.app.google_utils import get_google_access_token
    access_token = get_google_access_token()
    if not access_token:
        raise HTTPException(401, "Google not connected. Go to /auth/google first.")
    sheet_id = extract_sheet_id_from_url(request.sheet_url)
    if not sheet_id:
        raise HTTPException(400, "Invalid Google Sheets URL. Copy the full URL from your browser.")
    try:
        result = import_leads_from_sheet(db, access_token, sheet_id, request.sheet_tab or "Sheet1")
        if result.get("imported", 0) > 0:
            crud.log_agent_action(db, "system", "sheets_import", {"sheet_id": sheet_id},
                result, "success")
        return result
    except Exception as e:
        raise HTTPException(500, f"Sheets import failed: {str(e)}")


@app.get("/api/sheets/pipeline-url")
def sheets_get_pipeline_url(db: Session = Depends(get_db)):
    """Get (or create) the Omura Lead Pipeline sheet URL without exporting data."""
    from backend.app.google_sheets import get_or_create_pipeline_sheet, get_sheet_url
    from backend.app.google_utils import get_google_access_token
    access_token = get_google_access_token()
    if not access_token:
        raise HTTPException(401, "Google not connected. Go to /auth/google first.")
    try:
        sheet_id = get_or_create_pipeline_sheet(access_token)
        return {"sheet_id": sheet_id, "sheet_url": get_sheet_url(sheet_id)}
    except Exception as e:
        raise HTTPException(500, f"Could not get sheet: {str(e)}")


# ══════════════════════════════════════════════
# Google OAuth 2.0 — Real Auth Flow
# ══════════════════════════════════════════════

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_SCOPES = " ".join([
    "openid", "email", "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
])

@app.get("/auth/google")
def google_auth_start():
    """Redirect user to Google's OAuth consent screen."""
    from urllib.parse import urlencode
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI.strip(),
        "response_type": "code",
        "scope": _GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url)

@app.get("/auth/google/callback")
def google_auth_callback(code: str, db: Session = Depends(get_db)):
    """Exchange OAuth code for tokens and store them."""
    from backend.app.utils.security import store_token

    token_resp = _httpx.post(_GOOGLE_TOKEN_URL, data={
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI.strip(),
        "grant_type": "authorization_code",
    })

    if token_resp.status_code != 200:
        raise HTTPException(400, f"Token exchange failed: {token_resp.text}")

    token_data = token_resp.json()
    token_data["stored_at"] = datetime.utcnow().isoformat()
    store_token("google", token_data)

    crud.log_agent_action(db, "system", "google_oauth_connected", status="success")

    # Redirect back to dashboard with success flag
    frontend_url = _os.environ.get("FRONTEND_URL", "https://omura-life-manager.vercel.app")
    return RedirectResponse(f"{frontend_url}/?google_connected=1")

@app.get("/auth/google/status")
def google_auth_status():
    """Check if Google OAuth is connected."""
    from backend.app.utils.security import get_token
    token = get_token("google")
    return {
        "connected": token is not None,
        "has_refresh_token": bool(token and token.get("refresh_token")),
        "stored_at": token.get("stored_at") if token else None,
    }

@app.post("/auth/google/disconnect")
def google_auth_disconnect(db: Session = Depends(get_db)):
    """Revoke and delete stored Google tokens."""
    from backend.app.utils.security import delete_token, get_token
    token = get_token("google")
    if token and token.get("access_token"):
        try:
            _httpx.post(f"https://oauth2.googleapis.com/revoke?token={token['access_token']}")
        except Exception:
            pass
    delete_token("google")
    crud.log_agent_action(db, "system", "google_oauth_disconnected", status="success")
    return {"disconnected": True}


# ══════════════════════════════════════════════
# Sync Triggers — Real Gmail + Calendar
# ══════════════════════════════════════════════

@app.post("/api/sync/emails")
def sync_emails(db: Session = Depends(get_db)):
    """Sync emails from real Gmail API."""
    access_token = _get_google_access_token()
    if not access_token:
        return {"status": "not_connected", "message": "Connect Google at /auth/google first"}

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        # Get message list
        list_resp = _httpx.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers=headers,
            params={"maxResults": 30, "labelIds": "INBOX"},
        )
        if list_resp.status_code != 200:
            return {"status": "error", "message": list_resp.text}

        message_ids = [m["id"] for m in list_resp.json().get("messages", [])]
        saved = 0

        for msg_id in message_ids[:20]:
            existing = db.query(models.Communication).filter(
                models.Communication.external_id == msg_id
            ).first()

            # Fetch full message (needed for new records and to re-clean HTML bodies)
            msg_resp = _httpx.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                headers=headers,
                params={"format": "full"},
            )
            if msg_resp.status_code != 200:
                continue

            msg = msg_resp.json()
            headers_list = msg.get("payload", {}).get("headers", [])
            header_map = {h["name"].lower(): h["value"] for h in headers_list}

            subject = header_map.get("subject", "(no subject)")
            sender = header_map.get("from", "unknown")
            recipient = header_map.get("to", "")
            date_str = header_map.get("date", "")

            # Extract body — plain text preferred, HTML stripped as fallback
            payload = msg.get("payload", {})
            body = _extract_email_body(payload)

            labels = msg.get("labelIds", [])
            is_unread = "UNREAD" in labels

            try:
                received_at = datetime.strptime(date_str[:25].strip(), "%a, %d %b %Y %H:%M:%S") if date_str else datetime.utcnow()
            except Exception:
                received_at = datetime.utcnow()

            if existing:
                # Update body and subject in case it was stored as raw HTML before
                existing.body = body[:10000]
                existing.subject = subject[:500]
                existing.sender = sender[:255]
            else:
                comm = models.Communication(
                    platform="gmail",
                    external_id=msg_id,
                    sender=sender[:255],
                    recipient=recipient[:255],
                    subject=subject[:500],
                    body=body[:10000],
                    is_read=not is_unread,
                    labels=labels,
                    received_at=received_at,
                )
                db.add(comm)
                saved += 1

        db.commit()
        crud.log_agent_action(db, "system", "sync_emails", output_data={"saved": saved}, status="success")
        return {"status": "success", "synced": saved, "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/sync/calendar")
def sync_calendar(db: Session = Depends(get_db)):
    """Sync events from real Google Calendar API."""
    access_token = _get_google_access_token()
    if not access_token:
        return {"status": "not_connected", "message": "Connect Google at /auth/google first"}

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        now = datetime.utcnow()
        time_min = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        time_max = (now + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")

        resp = _httpx.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers=headers,
            params={"timeMin": time_min, "timeMax": time_max, "maxResults": 50, "singleEvents": "true", "orderBy": "startTime"},
        )
        if resp.status_code != 200:
            return {"status": "error", "message": resp.text}

        events = resp.json().get("items", [])
        saved = 0

        for ev in events:
            ev_id = ev.get("id")
            existing = db.query(models.CalendarEvent).filter(
                models.CalendarEvent.external_id == ev_id
            ).first()

            start = ev.get("start", {})
            end = ev.get("end", {})
            start_str = start.get("dateTime") or start.get("date", "")
            end_str = end.get("dateTime") or end.get("date", "")
            is_all_day = "date" in start and "dateTime" not in start

            try:
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00")).replace(tzinfo=None)
                end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                continue

            if existing:
                existing.title = ev.get("summary", "(no title)")[:500]
                existing.start_time = start_dt
                existing.end_time = end_dt
                existing.updated_at = datetime.utcnow()
            else:
                db.add(models.CalendarEvent(
                    external_id=ev_id,
                    title=ev.get("summary", "(no title)")[:500],
                    description=ev.get("description", ""),
                    location=ev.get("location", ""),
                    start_time=start_dt,
                    end_time=end_dt,
                    is_all_day=is_all_day,
                    source="google_calendar",
                ))
                saved += 1

        db.commit()
        crud.log_agent_action(db, "system", "sync_calendar", output_data={"saved": saved}, status="success")
        return {"status": "success", "synced": saved, "updated": len(events) - saved, "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/sync/social")
def sync_social(db: Session = Depends(get_db)):
    """Trigger social media sync."""
    crud.log_agent_action(db, "system", "sync_social", status="success")
    return {"status": "Social media sync triggered", "timestamp": datetime.utcnow().isoformat()}


# ══════════════════════════════════════════════
# Settings
# ══════════════════════════════════════════════

import json as _json_mod
import pathlib as _pathlib

_SETTINGS_FILE = _pathlib.Path(__file__).parent.parent / "settings.json"

@app.get("/api/settings")
def get_settings():
    """Get current user settings."""
    if _SETTINGS_FILE.exists():
        try:
            return _json_mod.loads(_SETTINGS_FILE.read_text())
        except Exception:
            pass
    return {
        "profile": {"name": "Damarley", "email": "sir@omura.app", "timezone": "America/Jamaica (EST)"},
        "notifications": {"email": True, "push": True, "sms": False, "weekly_scorecard": True},
        "agent_settings": {"auto_triage": True, "auto_respond": False, "auto_schedule": True,
                           "auto_followup": False, "daily_agenda": True, "health_tracking": True},
    }

@app.post("/api/settings")
def save_settings(data: SettingsUpdate):
    """Persist user settings to local file."""
    current = {}
    if _SETTINGS_FILE.exists():
        try:
            current = _json_mod.loads(_SETTINGS_FILE.read_text())
        except Exception:
            pass
    if data.profile:
        current["profile"] = data.profile
    if data.notifications:
        current["notifications"] = data.notifications
    if data.agent_settings:
        current["agent_settings"] = data.agent_settings
    _SETTINGS_FILE.write_text(_json_mod.dumps(current, indent=2))
    return {"status": "saved", "timestamp": datetime.utcnow().isoformat()}


# ══════════════════════════════════════════════
# Conversations — Multi-session chat management
# ══════════════════════════════════════════════

@app.get("/api/conversations")
def list_conversations(db: Session = Depends(get_db)):
    convs = db.query(models.Conversation).order_by(
        models.Conversation.updated_at.desc()
    ).limit(50).all()
    result = []
    for c in convs:
        last_msg = db.query(models.ChatMessage).filter(
            models.ChatMessage.conversation_id == c.id
        ).order_by(models.ChatMessage.created_at.desc()).first()
        result.append({
            "id": c.id,
            "title": c.title,
            "preview": (last_msg.content[:80] + "…") if last_msg and len(last_msg.content) > 80 else (last_msg.content if last_msg else ""),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        })
    return result

@app.post("/api/conversations")
def create_conversation(data: ConversationCreate, db: Session = Depends(get_db)):
    conv = models.Conversation(title=data.title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"id": conv.id, "title": conv.title, "created_at": conv.created_at.isoformat()}

@app.delete("/api/conversations/{conv_id}")
def delete_conversation(conv_id: int, db: Session = Depends(get_db)):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    db.delete(conv)
    db.commit()
    return {"deleted": True}

@app.get("/api/conversations/{conv_id}/messages")
def get_conversation_messages(conv_id: int, db: Session = Depends(get_db)):
    msgs = db.query(models.ChatMessage).filter(
        models.ChatMessage.conversation_id == conv_id
    ).order_by(models.ChatMessage.created_at.asc()).all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "agent_used": m.agent_used,
            "actions_taken": m.actions_taken or [],
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msgs
    ]

@app.post("/api/conversations/{conv_id}/chat")
def conversation_chat(conv_id: int, request: ConversationChatRequest, db: Session = Depends(get_db)):
    """Send a message within a specific conversation."""
    from backend.app.ai_agents.supervisor_ai import SupervisorAI

    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")

    # Auto-title the conversation from its first user message
    msg_count = db.query(models.ChatMessage).filter(
        models.ChatMessage.conversation_id == conv_id
    ).count()
    if msg_count == 0 and conv.title == "New Conversation":
        conv.title = request.message[:60] + ("…" if len(request.message) > 60 else "")

    user_msg = models.ChatMessage(role="user", content=request.message, conversation_id=conv_id)
    db.add(user_msg)
    conv.updated_at = datetime.utcnow()
    db.commit()

    try:
        supervisor = SupervisorAI(db)
        response = supervisor.chat(request.message)

        assistant_msg = models.ChatMessage(
            role="assistant",
            content=response.get("reply", ""),
            agent_used="supervisor",
            actions_taken=response.get("actions_taken", []),
            conversation_id=conv_id,
        )
        db.add(assistant_msg)
        conv.updated_at = datetime.utcnow()
        db.commit()

        return {
            "reply": response.get("reply", ""),
            "actions": response.get("actions_taken", []),
            "agent": "supervisor",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "reply": f"Error: {str(e)}. Please try again.",
            "actions": [],
            "agent": "supervisor",
            "error": True,
            "timestamp": datetime.utcnow().isoformat(),
        }


@app.post("/api/conversations/{conv_id}/chat/stream")
async def conversation_chat_stream(conv_id: int, request: ConversationChatRequest, db: Session = Depends(get_db)):
    """
    Async SSE streaming endpoint — emits real-time agent activity events.
    Events: thinking | tool_start | tool_done | done | error
    Each line: data: {"type": ..., ...}\n\n
    """
    import asyncio as _asyncio
    from backend.app.ai_agents.supervisor_ai import SupervisorAI
    from backend.app.database.session import SessionLocal

    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")

    # Auto-title
    msg_count = db.query(models.ChatMessage).filter(
        models.ChatMessage.conversation_id == conv_id
    ).count()
    if msg_count == 0 and conv.title == "New Conversation":
        conv.title = request.message[:60] + ("…" if len(request.message) > 60 else "")

    user_msg = models.ChatMessage(role="user", content=request.message, conversation_id=conv_id)
    db.add(user_msg)
    conv.updated_at = datetime.utcnow()
    db.commit()

    loop = _asyncio.get_event_loop()
    event_q: _asyncio.Queue = _asyncio.Queue()

    def on_event(etype: str, data: dict):
        # Called from background thread — schedule put on the event loop
        loop.call_soon_threadsafe(event_q.put_nowait, {"type": etype, **data})

    def run_chat():
        bg_db = SessionLocal()
        try:
            supervisor = SupervisorAI(bg_db, event_callback=on_event)
            response = supervisor.chat(request.message)
            asst_msg = models.ChatMessage(
                role="assistant",
                content=response.get("reply", ""),
                agent_used="supervisor",
                actions_taken=response.get("actions_taken", []),
                conversation_id=conv_id,
            )
            bg_db.add(asst_msg)
            bg_conv = bg_db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
            if bg_conv:
                bg_conv.updated_at = datetime.utcnow()
            bg_db.commit()
        except Exception as exc:
            loop.call_soon_threadsafe(event_q.put_nowait, {"type": "error", "message": str(exc)})
        finally:
            bg_db.close()
            loop.call_soon_threadsafe(event_q.put_nowait, None)  # sentinel

    _threading.Thread(target=run_chat, daemon=True).start()

    async def generate():
        # Immediate keepalive so Railway / proxies don't kill the connection before AI responds
        yield ": keepalive\n\n"
        while True:
            try:
                # Wait up to 20s then send a keepalive ping to hold the connection open
                item = await _asyncio.wait_for(event_q.get(), timeout=20)
            except _asyncio.TimeoutError:
                yield ": ping\n\n"
                continue
            if item is None:
                break
            yield f"data: {_json.dumps(item)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ══════════════════════════════════════════════
# Chat — Primary AI Interface
# ══════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Main conversational AI endpoint. Routes through SupervisorAI."""
    from backend.app.ai_agents.supervisor_ai import SupervisorAI

    try:
        supervisor = SupervisorAI(db)
        # supervisor.chat() saves both user and assistant messages internally
        response = supervisor.chat(request.message)

        return {
            "reply": response.get("reply", ""),
            "actions": response.get("actions_taken", []),
            "agent": "supervisor",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "reply": f"I encountered an error processing your request: {str(e)}. Please try again.",
            "actions": [],
            "agent": "supervisor",
            "error": True,
            "timestamp": datetime.utcnow().isoformat(),
        }


@app.delete("/api/chat/clear")
def clear_chat_history(db: Session = Depends(get_db)):
    """Wipe all chat history. Use when chat context is poisoned."""
    deleted = db.query(models.ChatMessage).delete()
    db.commit()
    return {"deleted": deleted, "message": "Chat history cleared."}

@app.get("/api/chat/history")
def chat_history(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve recent chat messages."""
    messages = db.query(models.ChatMessage).order_by(
        models.ChatMessage.created_at.desc()
    ).limit(limit).all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "agent_used": m.agent_used,
            "actions_taken": m.actions_taken,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in reversed(messages)
    ]


# ══════════════════════════════════════════════
# Apollo.io — Lead Enrichment & CRM Sync
# ══════════════════════════════════════════════

@app.get("/api/apollo/search")
async def apollo_search_people(
    q: Optional[str] = None,
    titles: Optional[str] = None,
    locations: Optional[str] = None,
    domains: Optional[str] = None,
    page: int = 1,
    per_page: int = 25,
):
    """Search Apollo.io for people matching criteria."""
    from backend.app.api.apollo_api import ApolloClient
    client = ApolloClient()
    try:
        result = await client.search_people(
            q_keywords=q,
            person_titles=titles.split(",") if titles else None,
            person_locations=locations.split(",") if locations else None,
            organization_domains=domains.split(",") if domains else None,
            page=page,
            per_page=per_page,
        )
        return result
    finally:
        await client.close()

@app.get("/api/apollo/enrich/person")
async def apollo_enrich_person(email: str):
    """Enrich a person's profile from their email via Apollo.io."""
    from backend.app.api.apollo_api import ApolloClient
    client = ApolloClient()
    try:
        return await client.enrich_person(email)
    finally:
        await client.close()

@app.get("/api/apollo/enrich/company")
async def apollo_enrich_company(domain: str):
    """Enrich a company's profile from their domain via Apollo.io."""
    from backend.app.api.apollo_api import ApolloClient
    client = ApolloClient()
    try:
        return await client.enrich_company(domain)
    finally:
        await client.close()

@app.post("/api/apollo/sync-lead/{lead_id}")
async def apollo_sync_lead(lead_id: int, db: Session = Depends(get_db)):
    """Push an Omura lead to Apollo and enrich with Apollo data."""
    from backend.app.api.apollo_api import ApolloClient

    lead = crud.get_record(db, models.Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")

    lead_data = {
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "company": lead.company,
        "extra_data": lead.extra_data or {},
    }

    client = ApolloClient()
    try:
        # Push to Apollo
        apollo_contact = await client.sync_lead_to_apollo(lead_data)

        # Enrich if email is available
        enrichment = {}
        if lead.email:
            enrichment = await client.pull_enrichment_for_lead(lead.email)
            # Update the lead with enriched data
            if enrichment.get("company"):
                lead.company = enrichment["company"]
            if enrichment.get("phone"):
                lead.phone = enrichment["phone"]
            existing_extra = lead.extra_data or {}
            existing_extra.update(enrichment.get("extra_data", {}))
            lead.extra_data = existing_extra
            db.commit()

        crud.log_agent_action(db, "apollo", "sync_lead", {"lead_id": lead_id}, apollo_contact, "success")
        return {
            "status": "synced",
            "apollo_contact": apollo_contact,
            "enrichment": enrichment,
            "lead_id": lead_id,
        }
    except Exception as e:
        crud.log_agent_action(db, "apollo", "sync_lead", {"lead_id": lead_id}, None, "error", str(e))
        raise HTTPException(500, f"Apollo sync failed: {str(e)}")
    finally:
        await client.close()

@app.get("/api/apollo/contacts")
async def apollo_search_contacts(q: str = "", page: int = 1, per_page: int = 25):
    """Search contacts in your Apollo account."""
    from backend.app.api.apollo_api import ApolloClient
    client = ApolloClient()
    try:
        return await client.search_contacts(q, page, per_page)
    finally:
        await client.close()


# ══════════════════════════════════════════════
# Outreach Pipeline — Autonomous Lead Gen & Personalized Outreach
# ══════════════════════════════════════════════

class OutreachPipelineRequest(BaseModel):
    titles: Optional[List[str]] = ["CEO", "Founder", "Owner", "Director"]
    locations: Optional[List[str]] = ["Jamaica"]
    industries: Optional[List[str]] = []
    manual_leads: Optional[List[dict]] = None
    domains: Optional[List[str]] = None  # company domains for Hunter.io search
    daily_limit: Optional[int] = 20

class VerifyEmailRequest(BaseModel):
    email: str

class SendInitialOutreachRequest(BaseModel):
    lead_id: int


@app.post("/api/outreach/run-pipeline")
def run_outreach_pipeline(request: OutreachPipelineRequest, db: Session = Depends(get_db)):
    """Find leads, verify emails, research each one, draft personalized copy, queue sequences."""
    from backend.app.ai_agents.outreach_ai import OutreachAI
    agent = OutreachAI(db)
    result = agent.run_pipeline(
        titles=request.titles,
        locations=request.locations,
        industries=request.industries,
        manual_leads=request.manual_leads,
        domains=request.domains,
        daily_limit=request.daily_limit,
    )
    return result


@app.post("/api/outreach/verify-email")
def verify_email_endpoint(request: VerifyEmailRequest):
    """Check if an email address is likely deliverable via MX record lookup."""
    from backend.app.ai_agents.outreach_ai import verify_email
    return verify_email(request.email)


@app.post("/api/outreach/send/{lead_id}")
def send_initial_outreach(lead_id: int, db: Session = Depends(get_db)):
    """Send the first outreach email to a lead using their researched + drafted copy."""
    from backend.app.ai_agents.outreach_ai import OutreachAI
    agent = OutreachAI(db)
    return agent.send_initial_outreach(lead_id)


class ResearchLeadRequest(BaseModel):
    email: str = ""
    name: str = ""
    company: str = ""
    website: str = ""

@app.post("/api/outreach/research")
def research_lead_endpoint(data: ResearchLeadRequest, db: Session = Depends(get_db)):
    """Research a single lead and draft personalized outreach copy."""
    from backend.app.ai_agents.outreach_ai import research_lead, draft_outreach_copy, verify_email
    email = data.email
    name = data.name
    company = data.company
    website = data.website

    verification = verify_email(email)
    research = research_lead(name, company, email, website)
    copy = draft_outreach_copy({"name": name, "company": company, "email": email}, research)

    return {
        "email_valid": verification["valid"],
        "verification_reason": verification["reason"],
        "research": research,
        "copy": copy,
    }


# ══════════════════════════════════════════════
# Google Drive — Document Storage
# ══════════════════════════════════════════════

@app.get("/api/drive/files")
async def drive_list_files(folder: Optional[str] = None, q: Optional[str] = None, page_size: int = 25):
    """List files in a Google Drive folder."""
    from backend.app.api.gdrive_api import GoogleDriveClient
    client = GoogleDriveClient()
    try:
        return await client.list_files(folder_name=folder, query=q, page_size=page_size)
    finally:
        await client.close()

@app.get("/api/drive/files/{file_id}")
async def drive_get_file(file_id: str):
    """Get metadata for a specific Google Drive file."""
    from backend.app.api.gdrive_api import GoogleDriveClient
    client = GoogleDriveClient()
    try:
        return await client.get_file(file_id)
    finally:
        await client.close()

@app.get("/api/drive/folders")
async def drive_folder_structure():
    """Get the Omura folder structure in Google Drive."""
    from backend.app.api.gdrive_api import GoogleDriveClient
    client = GoogleDriveClient()
    try:
        return await client.ensure_folder_structure()
    finally:
        await client.close()

@app.get("/api/drive/lead/{lead_name}/documents")
async def drive_lead_documents(lead_name: str):
    """List all documents for a specific lead in Google Drive."""
    from backend.app.api.gdrive_api import GoogleDriveClient
    client = GoogleDriveClient()
    try:
        return await client.get_lead_documents(lead_name)
    finally:
        await client.close()

@app.post("/api/drive/backup")
async def drive_backup(db: Session = Depends(get_db)):
    """Trigger a manual backup of Omura data to Google Drive."""
    import json as _json
    from backend.app.api.gdrive_api import GoogleDriveClient

    # Gather data for backup
    backup_data = {
        "leads": [{"id": l.id, "name": l.name, "email": l.email, "company": l.company, "status": l.status.value if l.status else None} for l in db.query(models.Lead).all()],
        "projects": [{"id": p.id, "name": p.name, "status": p.status.value if p.status else None} for p in db.query(models.Project).all()],
        "notes": [{"id": n.id, "title": n.title, "category": n.category} for n in db.query(models.Note).all()],
        "backed_up_at": datetime.utcnow().isoformat(),
    }

    client = GoogleDriveClient()
    try:
        result = await client.backup_data(_json.dumps(backup_data, indent=2).encode("utf-8"))
        crud.log_agent_action(db, "system", "drive_backup", None, result, "success")
        return {"status": "backup_complete", "file": result}
    except Exception as e:
        crud.log_agent_action(db, "system", "drive_backup", None, None, "error", str(e))
        raise HTTPException(500, f"Backup failed: {str(e)}")
    finally:
        await client.close()
