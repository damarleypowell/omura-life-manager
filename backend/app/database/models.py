"""
Omura Database Models
Unified schema covering: communications, projects, content, metrics, health, CRM, finance.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, JSON,
    ForeignKey, Enum as SAEnum, LargeBinary
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from backend.app.database.session import Base


# ── Enums ──

class UrgencyLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


class ContentStatus(str, enum.Enum):
    IDEA = "idea"
    DRAFT = "draft"
    REVIEW = "review"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"


class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    WON = "won"
    LOST = "lost"
    INVALID = "invalid"  # bad email / bounce / generic address — never retry


class Platform(str, enum.Enum):
    GMAIL = "gmail"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    WHATSAPP = "whatsapp"
    OTHER = "other"


# ── Models ──

class Communication(Base):
    """Unified inbox: emails, DMs, messages across all platforms."""
    __tablename__ = "communications"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(SAEnum(Platform), nullable=False)
    external_id = Column(String(255), unique=True)
    sender = Column(String(255))
    recipient = Column(String(255))
    subject = Column(String(500))
    body = Column(Text)
    summary = Column(Text)  # AI-generated summary
    urgency = Column(SAEnum(UrgencyLevel), default=UrgencyLevel.LOW)
    is_read = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)
    ai_suggested_response = Column(Text)
    labels = Column(JSON, default=list)
    extra_data = Column(JSON, default=dict)
    received_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Project(Base):
    """Projects with tasks, deadlines, and AI-predicted bottlenecks."""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.TODO)
    priority = Column(SAEnum(UrgencyLevel), default=UrgencyLevel.MEDIUM)
    deadline = Column(DateTime)
    progress_pct = Column(Float, default=0.0)
    ai_bottleneck_prediction = Column(Text)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    """Individual tasks within a project."""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.TODO)
    priority = Column(SAEnum(UrgencyLevel), default=UrgencyLevel.MEDIUM)
    due_date = Column(DateTime)
    source = Column(String(50))  # todoist, notion, google_calendar, manual
    external_id = Column(String(255))
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="tasks")


class ContentItem(Base):
    """Content pipeline: ideas → drafts → scheduled → published."""
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500))
    body = Column(Text)
    platform = Column(SAEnum(Platform))
    status = Column(SAEnum(ContentStatus), default=ContentStatus.IDEA)
    caption = Column(Text)
    hashtags = Column(JSON, default=list)
    media_urls = Column(JSON, default=list)
    scheduled_at = Column(DateTime)
    published_at = Column(DateTime)
    engagement_metrics = Column(JSON, default=dict)  # likes, shares, comments, reach
    ai_predicted_engagement = Column(Float)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Metric(Base):
    """Business KPIs, revenue, expenses, ad performance."""
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False)  # revenue, expense, ad_spend, kpi
    name = Column(String(255), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(50))  # USD, %, count
    source = Column(String(100))  # quickbooks, google_ads, facebook_ads, manual
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class HealthEntry(Base):
    """Health, fitness, sleep, and supplement tracking."""
    __tablename__ = "health_entries"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False)  # workout, sleep, supplement, nutrition
    name = Column(String(255))
    value = Column(Float)
    unit = Column(String(50))
    notes = Column(Text)
    source = Column(String(100))  # google_fit, apple_health, manual
    recorded_at = Column(DateTime, default=datetime.utcnow)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class Lead(Base):
    """CRM: leads, prospects, and clients."""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    company = Column(String(255))
    status = Column(SAEnum(LeadStatus), default=LeadStatus.NEW)
    score = Column(Float, default=0.0)  # AI-generated lead score 0-100
    source = Column(String(100))  # email, instagram, facebook, referral
    notes = Column(Text)
    last_contact = Column(DateTime)
    next_followup = Column(DateTime)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CalendarEvent(Base):
    """Synced calendar events from Google Calendar and other sources."""
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    location = Column(String(500))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_all_day = Column(Boolean, default=False)
    source = Column(String(50))  # google_calendar, manual
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Note(Base):
    """Knowledge hub: notes, research, strategy documents."""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    category = Column(String(100))  # research, strategy, idea, meeting_notes
    tags = Column(JSON, default=list)
    source = Column(String(50))  # notion, obsidian, manual
    external_id = Column(String(255))
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentLog(Base):
    """Audit trail for all AI agent actions."""
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(100), nullable=False)
    action = Column(String(255), nullable=False)
    input_data = Column(JSON)
    output_data = Column(JSON)
    status = Column(String(50))  # success, error, pending_approval
    error_message = Column(Text)
    duration_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class Scenario(Base):
    """What-if simulation results."""
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100))  # business, finance, content, life
    parameters = Column(JSON, nullable=False)
    results = Column(JSON)
    ai_recommendation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Conversation(Base):
    """Chat conversations — each is a distinct session with Omura AI."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Conversation history with the AI supervisor."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    agent_used = Column(String(100))  # which agent handled this, if any
    actions_taken = Column(JSON, default=list)  # what the AI did
    internet_requested = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class Credential(Base):
    """Encrypted credential storage for OAuth, API keys, etc."""
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)  # e.g. "google_client_id"
    service = Column(String(100), nullable=False)  # google, facebook, instagram, tiktok, bank
    credential_type = Column(String(50), nullable=False)  # client_id, client_secret, api_key, oauth_token
    encrypted_value = Column(LargeBinary, nullable=False)  # AES-256 encrypted
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InternetRequest(Base):
    """AI requests for internet access — must be approved before executing."""
    __tablename__ = "internet_requests"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(100), nullable=False)
    purpose = Column(Text, nullable=False)  # what the AI wants to do
    url_or_service = Column(String(500), nullable=False)  # where it wants to connect
    data_sent_description = Column(Text)  # what data will be sent
    data_received_description = Column(Text)  # what data will be received
    precautions = Column(Text)  # privacy protections in place
    status = Column(String(20), default="pending")  # pending, approved, denied, executed
    result = Column(JSON)  # result after execution
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)


class Campaign(Base):
    """Marketing campaigns being managed and optimized by AI."""
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    platform = Column(SAEnum(Platform))
    campaign_type = Column(String(100))  # outreach, content, ads, email
    status = Column(String(50), default="draft")  # draft, active, paused, completed
    target_audience = Column(Text)
    goals = Column(JSON, default=dict)  # target metrics
    current_metrics = Column(JSON, default=dict)  # actual performance
    ai_optimizations = Column(JSON, default=list)  # AI-suggested changes
    budget = Column(Float)
    spent = Column(Float, default=0.0)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ImportedContext(Base):
    """Parsed context from ChatGPT exports or other sources."""
    __tablename__ = "imported_contexts"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False)  # chatgpt, notes, manual
    title = Column(String(500))
    content = Column(Text, nullable=False)
    category = Column(String(100))  # goals, preferences, history, knowledge
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentInsight(Base):
    """Plain-English result of an agent/workflow run, tagged to the dashboard
    section it belongs to, so output shows up where the user expects it."""
    __tablename__ = "agent_insights"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(50), nullable=False)
    action = Column(String(100))
    section = Column(String(30), nullable=False, index=True)  # business|content|communication|health|scenarios|automation
    title = Column(String(255))
    summary = Column(Text)  # human-readable English — never raw JSON
    created_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════
# Titan Track — daily learning / leadership-development system
# (See TITAN_TRACK_SPEC. Status/tier/confidence stored as documented
#  strings — not SAEnum — so the schema works identically on SQLite and
#  Postgres without enum-type migrations. Array fields use JSON, matching
#  the rest of this schema, since SQLite has no native ARRAY type.)
# ══════════════════════════════════════════════════════════════════════

class LearningTrack(Base):
    """One learning track (Skill, Decision-Making, Leadership, Discipline,
    Stress, or the Horizon tier). Holds track-level progress."""
    __tablename__ = "learning_tracks"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)  # A, B, C, D, E, HORIZON
    name = Column(String(255), nullable=False)
    description = Column(Text)
    target_tier = Column(String(20), default="now")  # now | horizon
    cadence = Column(String(30), default="phase_gated")  # phase_gated | standing | quarterly
    progress_pct = Column(Float, default=0.0)
    color_theme = Column(String(20), default="#3B82F6")
    order_index = Column(Integer, default=0)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    modules = relationship("LearningModule", back_populates="track", cascade="all, delete-orphan")


class LearningModule(Base):
    """An individual topic within a track. Carries its research basis,
    confidence tag, prerequisites, and phase/sequencing metadata."""
    __tablename__ = "learning_modules"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("learning_tracks.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    tier = Column(String(20), default="now")  # now | horizon
    format = Column(String(30), default="course")  # course | case_study | dynamic_challenge | mixed
    source_material = Column(Text)  # links / reading suggestions
    research_basis = Column(Text)  # citation(s) the module rests on
    confidence_level = Column(String(20), default="moderate")  # strong | moderate | contested | theoretical
    confidence_note = Column(Text)  # the one-line "what this means" nuance for the UI badge
    prerequisite_ids = Column(JSON, default=list)  # list of module ids
    order_index = Column(Integer, default=0)
    status = Column(String(20), default="locked")  # locked | available | in_progress | mastered
    requires_failure_twin = Column(Boolean, default=False)
    week_number = Column(Integer, nullable=True)  # phase-gated sequencing; null = standing practice
    phase_code = Column(String(20), nullable=True)  # e.g. A1, C3
    culminating_artifact = Column(Text, nullable=True)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    track = relationship("LearningTrack", back_populates="modules")
    mastery_entries = relationship("MasteryEntry", back_populates="module", cascade="all, delete-orphan")


class MasteryEntry(Base):
    """One attempt at a module's gate — quiz score + explain-back result."""
    __tablename__ = "mastery_entries"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("learning_modules.id"), nullable=False)
    attempt_number = Column(Integer, default=1)
    quiz_score = Column(Float, default=0.0)  # 0-100
    quiz_answers = Column(JSON, default=dict)
    explain_back_transcript = Column(Text)
    explain_back_passed = Column(Boolean, default=False)
    ai_feedback = Column(Text)
    passed = Column(Boolean, default=False)  # quiz >= threshold AND explain_back_passed
    created_at = Column(DateTime, default=datetime.utcnow)

    module = relationship("LearningModule", back_populates="mastery_entries")


class LeadershipRep(Base):
    """A real leadership/presence rep — auto-pulled from Lead/Communication/
    CalendarEvent records flagged as calls/pitches/negotiations, or manual."""
    __tablename__ = "leadership_reps"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(40), default="manual")  # lead_call | pitch | negotiation | team_session | manual
    source_record_id = Column(Integer, nullable=True)  # FK-ish to Lead/Communication/CalendarEvent
    source_table = Column(String(40), nullable=True)  # which table source_record_id refers to
    date = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)
    ai_after_action_review = Column(Text)
    user_reflection = Column(Text, nullable=True)
    presence_score = Column(Float, nullable=True)  # 0-100, AI-estimated
    avoided_moments = Column(Text, nullable=True)  # "where you shrank"
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class StreakLog(Base):
    """Daily activity record — the don't-break-the-chain hook."""
    __tablename__ = "streak_logs"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), unique=True, nullable=False)  # YYYY-MM-DD
    tracks_touched = Column(JSON, default=list)
    total_minutes = Column(Integer, default=0)
    chain_intact = Column(Boolean, default=True)
    longest_streak_at_time = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class DailySession(Base):
    """The adaptive session container the Tutor AI assembles each day."""
    __tablename__ = "daily_sessions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), nullable=False, unique=True)  # YYYY-MM-DD — one session/day
    modules_assigned = Column(JSON, default=list)  # list of module ids
    session_payload = Column(JSON, default=dict)  # assembled concept/diagram/quiz/explain-back content
    leadership_rep_review_included = Column(Boolean, default=False)
    leadership_rep_id = Column(Integer, nullable=True)
    actual_minutes_spent = Column(Integer, default=0)
    energy_level_reported = Column(String(10), nullable=True)  # low | med | high
    started = Column(Boolean, default=False)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RoadmapSnapshot(Base):
    """Versioned copy of the roadmap so now/horizon plans can evolve
    without losing history."""
    __tablename__ = "roadmap_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(Integer, default=1)
    full_roadmap_json = Column(JSON, default=dict)
    change_note = Column(Text)
    compass_note = Column(Text, nullable=True)  # long-term "private city / eventual nation" bearing
    created_at = Column(DateTime, default=datetime.utcnow)


class SessionFeedback(Base):
    """QA Layer 4 — one-tap thumbs up/down after a session/module."""
    __tablename__ = "session_feedback"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("daily_sessions.id"), nullable=True)
    module_id = Column(Integer, nullable=True)
    thumbs = Column(String(10), nullable=False)  # up | down
    note = Column(Text, nullable=True)
    triggered_regeneration = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ModuleQualityCheck(Base):
    """QA Layer 2 — LLM-as-judge scores for a generated module's content."""
    __tablename__ = "module_quality_checks"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, nullable=True)
    generation_attempt = Column(Integer, default=1)
    judge_scores = Column(JSON, default=dict)  # one score per rubric dimension
    passed = Column(Boolean, default=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════
# Titan Track v2 — Duolingo-style scheduling, build-real-things projects,
# negotiation simulations, and weekly/monthly progress tests.
# ══════════════════════════════════════════════════════════════════════

class LessonSchedulePreference(Base):
    """The learner's preferred daily study slots (e.g. morning/afternoon/
    evening). Effectively a singleton — the latest row wins."""
    __tablename__ = "lesson_schedule_preferences"

    id = Column(Integer, primary_key=True, index=True)
    slots = Column(JSON, default=list)  # [{"slot":"morning","time":"08:00","track_pref":"A"}, ...]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ModuleProject(Base):
    """A build-real-things project attached to a learning module. Unlocked once
    the module's quiz is passed; graded by the Tutor AI against a rubric."""
    __tablename__ = "module_projects"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("learning_modules.id"), nullable=False, unique=True)  # one project per module
    brief = Column(JSON, default=dict)  # {title, description, steps[], starter_code, rubric, estimated_hours, submission_format}
    completed_steps = Column(JSON, default=list)  # list of step indices the learner has checked off
    submission_text = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    score = Column(Float, nullable=True)  # 0-100, AI-graded
    ai_feedback = Column(JSON, default=dict)  # {strengths[], improvements[], per_rubric, summary}
    status = Column(String(20), default="available")  # available | in_progress | submitted | graded
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NegotiationSession(Base):
    """A live AI-counterpart negotiation / leadership simulation. The AI plays
    the other side; the learner practices naming the ask and holding the line."""
    __tablename__ = "negotiation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("learning_modules.id"), nullable=True)
    scenario = Column(JSON, default=dict)  # {role, counterpart, objective, stakes, opening}
    rounds = Column(JSON, default=list)  # [{"role":"user"|"counterpart","text":"...","ts":"..."}]
    outcome = Column(JSON, nullable=True)  # {score, analysis, what_worked[], what_cost_you[]}
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProgressTest(Base):
    """A weekly or monthly multi-module review test. Questions carry an internal
    answer key (stripped before serialization); grading reports per-track scores."""
    __tablename__ = "progress_tests"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False)  # weekly | monthly
    period_start = Column(String(10))  # YYYY-MM-DD
    period_end = Column(String(10))    # YYYY-MM-DD
    questions = Column(JSON, default=list)  # [{question, options[], correct, explanation, module_id, track_code}]
    answers = Column(JSON, nullable=True)  # list of chosen option indices
    submitted_at = Column(DateTime, nullable=True)
    score_overall = Column(Float, nullable=True)
    scores_by_track = Column(JSON, nullable=True)  # {"A":82,"B":60,...}
    created_at = Column(DateTime, default=datetime.utcnow)
