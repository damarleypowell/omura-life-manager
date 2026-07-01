"""
Omura Life Manager — Centralized Logging
=========================================
Provides a unified logging interface for every AI agent and backend service.
All entries are written to both the console and a rotating log file so that
operational history is always available for debugging and auditing.

Usage::

    from backend.app.utils.logging import log_action, log_error, get_recent_logs

    log_action("EmailAgent", "fetch_inbox", "Retrieved 42 new messages")
    log_error("CalendarAgent", "Google API returned 403 Forbidden")
    recent = get_recent_logs("EmailAgent", limit=20)
"""

from __future__ import annotations

import logging
import os
from collections import deque
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from threading import Lock
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
DEFAULT_LOG_FILE = os.path.join(LOG_DIR, "omura.log")
LOG_FORMAT = "[%(asctime)s] [%(agent_name)s] [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_LOG_BYTES = 10 * 1024 * 1024  # 10 MB per file
BACKUP_COUNT = 5
DEFAULT_RECENT_LIMIT = 50


# ---------------------------------------------------------------------------
# In-memory ring buffer for fast recent-log retrieval
# ---------------------------------------------------------------------------
_LOG_BUFFER_SIZE = 2000
_log_buffers: Dict[str, deque] = {}
_buffer_lock = Lock()


def _store_entry(agent_name: str, entry: dict) -> None:
    """Append a log entry to the per-agent in-memory ring buffer."""
    with _buffer_lock:
        if agent_name not in _log_buffers:
            _log_buffers[agent_name] = deque(maxlen=_LOG_BUFFER_SIZE)
        _log_buffers[agent_name].append(entry)


# ---------------------------------------------------------------------------
# Custom logging helpers
# ---------------------------------------------------------------------------

class _AgentFilter(logging.Filter):
    """Inject *agent_name* into every ``LogRecord`` so the formatter can
    reference ``%(agent_name)s`` without raising a ``KeyError``."""

    def __init__(self, agent_name: str = "system") -> None:
        super().__init__()
        self.agent_name = agent_name

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "agent_name"):
            record.agent_name = self.agent_name  # type: ignore[attr-defined]
        return True


# ---------------------------------------------------------------------------
# OmuraLogger
# ---------------------------------------------------------------------------

class OmuraLogger:
    """Centralised logger that writes to both a rotating file and the console.

    Each ``OmuraLogger`` instance is bound to a specific *agent_name* so that
    downstream code can simply call ``logger.info(msg)`` without having to
    pass the agent name every time.

    Parameters
    ----------
    agent_name:
        Human-readable identifier for the agent or service (e.g.
        ``"EmailAgent"``, ``"SchedulerService"``).
    log_file:
        Path to the log file.  Defaults to ``<project>/backend/logs/omura.log``.
    level:
        Minimum log level.  Defaults to ``logging.DEBUG``.
    """

    def __init__(
        self,
        agent_name: str = "system",
        log_file: str = DEFAULT_LOG_FILE,
        level: int = logging.DEBUG,
    ) -> None:
        self.agent_name = agent_name

        # Ensure the log directory exists.
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Use a namespaced Python logger so multiple OmuraLogger instances
        # coexist without duplicating handlers on the root logger.
        self._logger = logging.getLogger(f"omura.{agent_name}")
        self._logger.setLevel(level)
        self._logger.addFilter(_AgentFilter(agent_name))

        # Avoid adding duplicate handlers if the logger already exists.
        if not self._logger.handlers:
            formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

            # ── File handler (rotating) ──
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=MAX_LOG_BYTES,
                backupCount=BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

            # ── Console handler ──
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)

    # -- convenience wrappers ------------------------------------------------

    # NOTE: every wrapper accepts *args (printf-style or extra positionals) and
    # **kwargs (structured fields). Logging must NEVER crash the caller — a bad
    # log call previously raised TypeError and turned agent fallbacks into 500s.

    def debug(self, message: str = "", *args, **kwargs) -> None:
        """Log a DEBUG-level message."""
        self._emit(logging.DEBUG, message, *args, **kwargs)

    def info(self, message: str = "", *args, **kwargs) -> None:
        """Log an INFO-level message."""
        self._emit(logging.INFO, message, *args, **kwargs)

    def warning(self, message: str = "", *args, **kwargs) -> None:
        """Log a WARNING-level message."""
        self._emit(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str = "", *args, **kwargs) -> None:
        """Log an ERROR-level message."""
        self._emit(logging.ERROR, message, *args, **kwargs)

    def critical(self, message: str = "", *args, **kwargs) -> None:
        """Log a CRITICAL-level message."""
        self._emit(logging.CRITICAL, message, *args, **kwargs)

    # -- internal ------------------------------------------------------------

    def _emit(self, level: int, message: str, *args, **kwargs) -> None:
        """Write to the Python logger and the ring buffer. Never raises."""
        try:
            msg = str(message)
            if args:
                # Support printf-style ("...%s", val) and tolerate mismatches.
                try:
                    msg = msg % args
                except Exception:
                    msg = msg + " " + " ".join(str(a) for a in args)
            if kwargs:
                context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
                msg = f"{msg} | {context}"
            self._logger.log(level, msg, extra={"agent_name": self.agent_name})
            _store_entry(
                self.agent_name,
                {
                    "timestamp": datetime.now(timezone.utc).strftime(DATE_FORMAT),
                    "agent_name": self.agent_name,
                    "level": logging.getLevelName(level),
                    "message": msg,
                },
            )
        except Exception:
            pass  # logging must never crash the caller


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------
# These keep call-sites concise — no need to instantiate a logger first.

# Cache of OmuraLogger instances keyed by agent name.
_loggers: Dict[str, OmuraLogger] = {}
_loggers_lock = Lock()


def _get_logger(agent_name: str) -> OmuraLogger:
    """Return (or create) a cached ``OmuraLogger`` for *agent_name*."""
    with _loggers_lock:
        if agent_name not in _loggers:
            _loggers[agent_name] = OmuraLogger(agent_name=agent_name)
        return _loggers[agent_name]


def log_action(agent_name: str, action: str, details: str = "") -> None:
    """Log an agent action at INFO level.

    Parameters
    ----------
    agent_name:
        Identifier of the agent performing the action.
    action:
        Short verb/noun label (e.g. ``"fetch_inbox"``).
    details:
        Optional human-readable description of what happened.

    Example::

        log_action("EmailAgent", "fetch_inbox", "42 new messages")
    """
    message = f"ACTION={action}"
    if details:
        message += f" | {details}"
    _get_logger(agent_name).info(message)


def log_error(agent_name: str, error: str) -> None:
    """Log an error for a specific agent at ERROR level.

    Parameters
    ----------
    agent_name:
        Identifier of the agent that encountered the error.
    error:
        Description of the error (may include a traceback string).

    Example::

        log_error("CalendarAgent", "Google API returned 403 Forbidden")
    """
    _get_logger(agent_name).error(error)


def get_recent_logs(
    agent_name: str,
    limit: int = DEFAULT_RECENT_LIMIT,
) -> List[dict]:
    """Return the most recent log entries for *agent_name*.

    Entries are returned newest-first.  Each entry is a dict with keys:
    ``timestamp``, ``agent_name``, ``level``, ``message``.

    Parameters
    ----------
    agent_name:
        The agent whose logs should be retrieved.
    limit:
        Maximum number of entries to return.  Defaults to 50.

    Returns
    -------
    list[dict]
        A list of log-entry dicts, newest first.
    """
    with _buffer_lock:
        buf = _log_buffers.get(agent_name, deque())
        # Return newest first.
        entries = list(buf)[-limit:]
        entries.reverse()
        return entries


def get_all_recent_logs(limit: int = DEFAULT_RECENT_LIMIT) -> List[dict]:
    """Return the most recent log entries across **all** agents.

    Entries are merged, sorted by timestamp (newest first), and truncated to
    *limit*.
    """
    with _buffer_lock:
        merged: List[dict] = []
        for buf in _log_buffers.values():
            merged.extend(buf)
    merged.sort(key=lambda e: e["timestamp"], reverse=True)
    return merged[:limit]
