"""
Shared scheduler instance and job registration — avoids circular imports.
Imported by main.py (to start) and by agents (to schedule jobs).
"""
from __future__ import annotations
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

scheduler = BackgroundScheduler(timezone="UTC")


def schedule_lead_followup_sequence(lead_id: int):
    """Queue day-3, day-7, day-14 follow-up emails for a lead."""
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
