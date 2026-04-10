"""
CRUD operations for all Omura models.
Generic helpers + model-specific queries.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json

from backend.app.database.models import (
    Communication, Project, Task, ContentItem, Metric,
    HealthEntry, Lead, CalendarEvent, Note, AgentLog, Scenario,
    UrgencyLevel, TaskStatus, ContentStatus, LeadStatus
)
from backend.app.database.session import get_redis


# ── Generic CRUD Helpers ──

def create_record(db: Session, model_class, **kwargs):
    """Create a new record of any model type."""
    try:
        record = model_class(**kwargs)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception:
        db.rollback()
        raise


def get_record(db: Session, model_class, record_id: int):
    """Get a single record by ID."""
    return db.query(model_class).filter(model_class.id == record_id).first()


def get_records(db: Session, model_class, skip: int = 0, limit: int = 100, **filters):
    """Get multiple records with optional filtering."""
    query = db.query(model_class)
    for key, value in filters.items():
        if hasattr(model_class, key) and value is not None:
            query = query.filter(getattr(model_class, key) == value)
    return query.order_by(desc(model_class.created_at)).offset(skip).limit(limit).all()


def update_record(db: Session, model_class, record_id: int, **kwargs):
    """Update a record by ID."""
    record = db.query(model_class).filter(model_class.id == record_id).first()
    if not record:
        return None
    for key, value in kwargs.items():
        if hasattr(record, key):
            setattr(record, key, value)
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, model_class, record_id: int):
    """Delete a record by ID."""
    record = db.query(model_class).filter(model_class.id == record_id).first()
    if record:
        db.delete(record)
        db.commit()
        return True
    return False


# ── Communication Queries ──

def get_unread_communications(db: Session, platform: str = None, limit: int = 50):
    query = db.query(Communication).filter(Communication.is_read == False)
    if platform:
        query = query.filter(Communication.platform == platform)
    return query.order_by(desc(Communication.received_at)).limit(limit).all()


def get_flagged_communications(db: Session, limit: int = 50):
    return (
        db.query(Communication)
        .filter(Communication.is_flagged == True)
        .order_by(desc(Communication.received_at))
        .limit(limit)
        .all()
    )


def get_urgent_communications(db: Session):
    return (
        db.query(Communication)
        .filter(Communication.urgency.in_([UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]))
        .filter(Communication.is_read == False)
        .order_by(desc(Communication.received_at))
        .all()
    )


# ── Project & Task Queries ──

def get_active_projects(db: Session):
    return (
        db.query(Project)
        .filter(Project.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS]))
        .order_by(Project.deadline)
        .all()
    )


def get_overdue_tasks(db: Session):
    return (
        db.query(Task)
        .filter(Task.status != TaskStatus.DONE)
        .filter(Task.due_date < datetime.utcnow())
        .order_by(Task.due_date)
        .all()
    )


def get_tasks_due_today(db: Session):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    today_end = today_start + timedelta(days=1)
    return (
        db.query(Task)
        .filter(Task.status != TaskStatus.DONE)
        .filter(and_(Task.due_date >= today_start, Task.due_date < today_end))
        .all()
    )


# ── Content Queries ──

def get_content_pipeline(db: Session):
    return (
        db.query(ContentItem)
        .filter(ContentItem.status != ContentStatus.PUBLISHED)
        .order_by(ContentItem.scheduled_at)
        .all()
    )


def get_scheduled_content(db: Session, platform: str = None):
    query = db.query(ContentItem).filter(ContentItem.status == ContentStatus.SCHEDULED)
    if platform:
        query = query.filter(ContentItem.platform == platform)
    return query.order_by(ContentItem.scheduled_at).all()


# ── Metric Queries ──

def get_metrics_by_category(db: Session, category: str, days: int = 30):
    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(Metric)
        .filter(Metric.category == category)
        .filter(Metric.created_at >= since)
        .order_by(desc(Metric.created_at))
        .all()
    )


def get_kpi_summary(db: Session, days: int = 30):
    """Aggregate KPIs for dashboard display."""
    since = datetime.utcnow() - timedelta(days=days)
    metrics = (
        db.query(Metric)
        .filter(Metric.created_at >= since)
        .all()
    )
    summary = {}
    for m in metrics:
        key = f"{m.category}_{m.name}"
        if key not in summary:
            summary[key] = {"total": 0, "count": 0, "unit": m.unit}
        summary[key]["total"] += m.value
        summary[key]["count"] += 1
    return summary


# ── Health Queries ──

def get_health_entries(db: Session, category: str = None, days: int = 7):
    since = datetime.utcnow() - timedelta(days=days)
    query = db.query(HealthEntry).filter(HealthEntry.recorded_at >= since)
    if category:
        query = query.filter(HealthEntry.category == category)
    return query.order_by(desc(HealthEntry.recorded_at)).all()


# ── Lead / CRM Queries ──

def get_leads_needing_followup(db: Session):
    return (
        db.query(Lead)
        .filter(Lead.next_followup <= datetime.utcnow())
        .filter(Lead.status.notin_([LeadStatus.WON, LeadStatus.LOST]))
        .order_by(Lead.next_followup)
        .all()
    )


def get_hot_leads(db: Session, min_score: float = 70.0):
    return (
        db.query(Lead)
        .filter(Lead.score >= min_score)
        .filter(Lead.status.notin_([LeadStatus.WON, LeadStatus.LOST]))
        .order_by(desc(Lead.score))
        .all()
    )


# ── Calendar Queries ──

def get_todays_events(db: Session):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    today_end = today_start + timedelta(days=1)
    return (
        db.query(CalendarEvent)
        .filter(and_(CalendarEvent.start_time >= today_start, CalendarEvent.start_time < today_end))
        .order_by(CalendarEvent.start_time)
        .all()
    )


def get_upcoming_events(db: Session, days: int = 7):
    until = datetime.utcnow() + timedelta(days=days)
    return (
        db.query(CalendarEvent)
        .filter(CalendarEvent.start_time >= datetime.utcnow())
        .filter(CalendarEvent.start_time <= until)
        .order_by(CalendarEvent.start_time)
        .all()
    )


# ── Agent Log Queries ──

def log_agent_action(db: Session, agent_name: str, action: str,
                     input_data: dict = None, output_data: dict = None,
                     status: str = "success", error_message: str = None,
                     duration_ms: int = None):
    # Only rollback if the session has a failed transaction
    try:
        if not db.is_active:
            db.rollback()
    except Exception:
        pass
    try:
        return create_record(
            db, AgentLog,
            agent_name=agent_name, action=action,
            input_data=input_data, output_data=output_data,
            status=status, error_message=error_message,
            duration_ms=duration_ms
        )
    except Exception:
        pass  # logging must never crash the caller


def get_agent_logs(db: Session, agent_name: str = None, limit: int = 100):
    query = db.query(AgentLog)
    if agent_name:
        query = query.filter(AgentLog.agent_name == agent_name)
    return query.order_by(desc(AgentLog.created_at)).limit(limit).all()


# ── Redis Cache Helpers ──

def cache_set(key: str, value: Any, ttl: int = 300):
    """Cache a value in Redis with TTL in seconds."""
    r = get_redis()
    if r:
        r.setex(key, ttl, json.dumps(value, default=str))


def cache_get(key: str) -> Optional[Any]:
    """Get a cached value from Redis."""
    r = get_redis()
    if not r:
        return None
    data = r.get(key)
    return json.loads(data) if data else None


def cache_delete(key: str):
    """Delete a cached value."""
    r = get_redis()
    if r:
        r.delete(key)
