"""
Shared scheduler instance and job registration — avoids circular imports.
Imported by main.py (to start) and by agents (to schedule jobs).

Uses SQLAlchemy job store so follow-up sequences survive Railway restarts/redeploys.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor


def _make_scheduler() -> BackgroundScheduler:
    """Build scheduler with PostgreSQL job store for persistence across restarts."""
    from backend.app.config import settings

    jobstores = {
        "default": SQLAlchemyJobStore(url=settings.DATABASE_URL),
    }
    executors = {
        "default": ThreadPoolExecutor(10),
    }
    job_defaults = {
        "coalesce": True,       # merge missed runs into one
        "max_instances": 1,     # prevent overlapping executions
        "misfire_grace_time": 3600,  # run jobs up to 1h late if server was down
    }

    return BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone="UTC",
    )


scheduler = _make_scheduler()


def schedule_lead_followup_sequence(lead_id: int):
    """Queue the research-grounded 30-day follow-up sequence for a lead.

    Touches come from outreach_ai.FOLLOWUP_SEQUENCE (day 0 opener is sent
    immediately by send_initial_outreach, so it's skipped here):
      • email touches  -> auto-sent via send_followup_email
      • LinkedIn/call  -> a Task is created for Damarley via create_followup_task
    Jobs are persisted in the scheduler job store — survive restarts.
    """
    from backend.app.scheduler_jobs import send_followup_email, create_followup_task
    from backend.app.ai_agents.outreach_ai import FOLLOWUP_SEQUENCE

    now = datetime.utcnow()
    for touch in FOLLOWUP_SEQUENCE:
        day = touch["day"]
        if day <= 0:
            continue  # day-0 opener handled by send_initial_outreach
        run_time = now + timedelta(days=day)
        if touch["channel"] == "email":
            scheduler.add_job(
                send_followup_email, "date", run_date=run_time,
                args=[lead_id, day], id=f"followup_lead{lead_id}_day{day}",
                replace_existing=True,
            )
        else:  # linkedin / call -> actionable task for Damarley
            scheduler.add_job(
                create_followup_task, "date", run_date=run_time,
                args=[lead_id, day], id=f"followuptask_lead{lead_id}_day{day}",
                replace_existing=True,
            )
