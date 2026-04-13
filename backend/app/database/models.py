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
