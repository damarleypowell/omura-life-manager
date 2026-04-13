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
    """Queue Touch 2/3/4 follow-up emails for a lead.

    Schedule:
      Touch 1 = day 0  (sent immediately by send_initial_outreach)
      Touch 2 = day 3
      Touch 3 = day 7
      Touch 4 = day 14
      Loom    = triggered on reply (not scheduled here)

    Jobs are persisted in PostgreSQL — survive Railway restarts.
    """
    from backend.app.scheduler_jobs import send_followup_email
    now = datetime.utcnow()
    for day in (3, 7, 14):
        run_time = now + timedelta(days=day)
        job_id = f"followup_lead{lead_id}_day{day}"
        scheduler.add_job(
            send_followup_email,
            "date",
            run_date=run_time,
            args=[lead_id, day],
            id=job_id,
            replace_existing=True,
        )
