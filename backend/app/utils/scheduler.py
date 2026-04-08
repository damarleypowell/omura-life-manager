"""
Omura Life Manager — Task Scheduler
=====================================
APScheduler-based task scheduler that manages recurring background jobs
such as syncing e-mail, calendar events, social-media feeds, and generating
daily reports.

Usage::

    from backend.app.utils.scheduler import omura_scheduler

    omura_scheduler.start()          # kick off all pre-registered jobs
    omura_scheduler.list_jobs()      # inspect what is scheduled
    omura_scheduler.shutdown()       # graceful teardown

Custom jobs can be registered at any time::

    omura_scheduler.add_job(
        func=my_function,
        trigger="interval",
        minutes=15,
        id="my_custom_job",
    )
"""

from __future__ import annotations

import atexit
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobEvent
from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from backend.app.utils.logging import log_action, log_error

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_AGENT_NAME = "Scheduler"


# ---------------------------------------------------------------------------
# Pre-built placeholder tasks
# ---------------------------------------------------------------------------


def sync_emails() -> None:
    """Placeholder — synchronise the user's e-mail inboxes.

    In production this would call the EmailAgent to fetch new messages,
    classify them, and surface anything requiring attention.
    """
    log_action(
        _AGENT_NAME,
        "sync_emails",
        "Email sync triggered (placeholder — no actual sync performed).",
    )


def sync_calendar() -> None:
    """Placeholder — synchronise calendar events from connected providers.

    In production this would call the CalendarAgent to pull events from
    Google Calendar, Outlook, etc.
    """
    log_action(
        _AGENT_NAME,
        "sync_calendar",
        "Calendar sync triggered (placeholder — no actual sync performed).",
    )


def sync_social() -> None:
    """Placeholder — synchronise social-media feeds and notifications.

    In production this would call the SocialMediaAgent to pull updates
    from Facebook, Instagram, TikTok, YouTube, etc.
    """
    log_action(
        _AGENT_NAME,
        "sync_social",
        "Social media sync triggered (placeholder — no actual sync performed).",
    )


def generate_daily_report() -> None:
    """Placeholder — generate and deliver the user's daily summary report.

    In production this would aggregate data from all agents, compile
    insights, and deliver the report via the user's preferred channel.
    """
    log_action(
        _AGENT_NAME,
        "generate_daily_report",
        "Daily report generation triggered (placeholder — no actual report generated).",
    )


# ---------------------------------------------------------------------------
# OmuraScheduler
# ---------------------------------------------------------------------------


class OmuraScheduler:
    """Wrapper around APScheduler's ``BackgroundScheduler`` with sensible
    defaults and convenience helpers.

    The scheduler is configured with a thread-pool executor (for I/O-bound
    tasks) and a process-pool executor (for CPU-bound tasks).  Jobs are
    stored in memory by default; swap in a persistent job store (e.g.
    SQLAlchemy or Redis) for durability across restarts.

    Parameters
    ----------
    auto_register_defaults:
        When ``True`` (the default) the four built-in placeholder tasks
        are registered automatically on :meth:`start`.
    """

    def __init__(self, auto_register_defaults: bool = True) -> None:
        self._auto_register_defaults = auto_register_defaults
        self._running = False

        job_stores = {
            "default": MemoryJobStore(),
        }
        executors = {
            "default": ThreadPoolExecutor(max_workers=10),
            "processpool": ProcessPoolExecutor(max_workers=3),
        }
        job_defaults = {
            "coalesce": True,           # collapse missed runs into one
            "max_instances": 1,         # avoid overlapping runs
            "misfire_grace_time": 300,  # 5-minute grace window
        }

        self._scheduler = BackgroundScheduler(
            jobstores=job_stores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

        # Listen for job outcomes so we can log successes and failures.
        self._scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self._scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)

    # -- Lifecycle -----------------------------------------------------------

    def start(self) -> None:
        """Start the scheduler.

        If *auto_register_defaults* was ``True`` at construction time, the
        four built-in placeholder tasks are registered before the scheduler
        begins processing.
        """
        if self._running:
            log_action(_AGENT_NAME, "start", "Scheduler is already running.")
            return

        if self._auto_register_defaults:
            self._register_default_jobs()

        self._scheduler.start()
        self._running = True
        atexit.register(self.shutdown)
        log_action(_AGENT_NAME, "start", "Scheduler started successfully.")

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the scheduler gracefully.

        Parameters
        ----------
        wait:
            If ``True`` (the default), block until all running jobs finish.
        """
        if not self._running:
            return
        self._scheduler.shutdown(wait=wait)
        self._running = False
        log_action(_AGENT_NAME, "shutdown", "Scheduler shut down successfully.")

    @property
    def is_running(self) -> bool:
        """Return ``True`` if the scheduler is currently active."""
        return self._running

    # -- Job management ------------------------------------------------------

    def add_job(
        self,
        func: Callable[..., Any],
        trigger: str,
        id: Optional[str] = None,
        replace_existing: bool = True,
        **kwargs: Any,
    ) -> str:
        """Add a job to the scheduler.

        Parameters
        ----------
        func:
            The callable to execute.
        trigger:
            APScheduler trigger type — ``"interval"``, ``"cron"``, or
            ``"date"``.
        id:
            Optional unique job identifier.  If omitted, APScheduler
            generates one automatically.
        replace_existing:
            When ``True``, an existing job with the same *id* is silently
            replaced.
        **kwargs:
            Additional keyword arguments forwarded to
            ``BackgroundScheduler.add_job`` (e.g. ``minutes=15``,
            ``hour=8``, ``day_of_week="mon-fri"``).

        Returns
        -------
        str
            The job ID (generated or provided).
        """
        job = self._scheduler.add_job(
            func,
            trigger=trigger,
            id=id,
            replace_existing=replace_existing,
            **kwargs,
        )
        log_action(
            _AGENT_NAME,
            "add_job",
            f"Job '{job.id}' added (trigger={trigger}).",
        )
        return job.id

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job by its ID.

        Parameters
        ----------
        job_id:
            The unique identifier of the job to remove.

        Returns
        -------
        bool
            ``True`` if the job was removed, ``False`` if it was not found.
        """
        try:
            self._scheduler.remove_job(job_id)
            log_action(
                _AGENT_NAME,
                "remove_job",
                f"Job '{job_id}' removed.",
            )
            return True
        except Exception:
            log_error(
                _AGENT_NAME,
                f"Failed to remove job '{job_id}' — job not found.",
            )
            return False

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Return a summary of all currently scheduled jobs.

        Returns
        -------
        list[dict]
            Each dict contains ``id``, ``name``, ``trigger``, and
            ``next_run_time``.
        """
        jobs = self._scheduler.get_jobs()
        result: List[Dict[str, Any]] = []
        for job in jobs:
            next_run = (
                job.next_run_time.isoformat()
                if job.next_run_time
                else None
            )
            result.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "trigger": str(job.trigger),
                    "next_run_time": next_run,
                }
            )
        log_action(
            _AGENT_NAME,
            "list_jobs",
            f"Listed {len(result)} scheduled job(s).",
        )
        return result

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Return details for a single job, or ``None`` if not found."""
        job = self._scheduler.get_job(job_id)
        if job is None:
            return None
        next_run = (
            job.next_run_time.isoformat() if job.next_run_time else None
        )
        return {
            "id": job.id,
            "name": job.name,
            "trigger": str(job.trigger),
            "next_run_time": next_run,
        }

    # -- Default jobs --------------------------------------------------------

    def _register_default_jobs(self) -> None:
        """Register the four built-in recurring tasks."""
        self.add_job(
            func=sync_emails,
            trigger="interval",
            id="sync_emails",
            minutes=15,
            name="Sync Emails",
        )
        self.add_job(
            func=sync_calendar,
            trigger="interval",
            id="sync_calendar",
            minutes=30,
            name="Sync Calendar",
        )
        self.add_job(
            func=sync_social,
            trigger="interval",
            id="sync_social",
            minutes=60,
            name="Sync Social Media",
        )
        self.add_job(
            func=generate_daily_report,
            trigger="cron",
            id="generate_daily_report",
            hour=7,
            minute=0,
            name="Generate Daily Report",
        )
        log_action(
            _AGENT_NAME,
            "register_defaults",
            "Registered 4 default scheduled tasks.",
        )

    # -- Event listeners -----------------------------------------------------

    @staticmethod
    def _on_job_executed(event: JobEvent) -> None:
        """Log successful job executions."""
        log_action(
            _AGENT_NAME,
            "job_executed",
            f"Job '{event.job_id}' completed successfully.",
        )

    @staticmethod
    def _on_job_error(event: JobEvent) -> None:
        """Log job failures."""
        log_error(
            _AGENT_NAME,
            f"Job '{event.job_id}' failed: {event.exception}",
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
omura_scheduler = OmuraScheduler()
