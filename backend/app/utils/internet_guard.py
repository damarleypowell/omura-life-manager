"""
Omura Life Manager — Internet Access Guard
============================================
Permission system that ensures **no AI agent can access the internet**
without explicit, prior user approval.

Every outbound request is modelled as an :class:`InternetRequest` row that
starts in ``"pending"`` status.  The user (or an admin endpoint) must
approve or deny each request before execution can proceed.

Workflow
--------
1. Agent calls :func:`request_access` describing *what* it wants to do,
   *where* it will connect, *what data* it will send/receive, and *what
   precautions* it will take.
2. The request is surfaced to the user via the dashboard / chat
   (:func:`format_request_for_user` produces a human-readable summary).
3. The user calls :func:`approve_request` or :func:`deny_request`.
4. Only after approval can the agent call :func:`execute_approved_request`,
   which runs a caller-supplied *executor_func* and stores the result.

Usage::

    from backend.app.utils.internet_guard import (
        request_access, approve_request, deny_request,
        get_pending_requests, execute_approved_request,
        format_request_for_user,
    )
"""

from __future__ import annotations

import logging
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.app.database.models import InternetRequest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Request lifecycle helpers
# ---------------------------------------------------------------------------


def request_access(
    db: Session,
    agent_name: str,
    purpose: str,
    url_or_service: str,
    data_sent_description: str,
    precautions: str,
) -> InternetRequest:
    """Create a new **pending** internet-access request.

    This is the *only* entry point for agents that need to reach the
    network.  The request is persisted immediately so it can be surfaced
    to the user for review.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    agent_name:
        Identifier of the requesting agent (e.g. ``"email_agent"``).
    purpose:
        Plain-English explanation of *why* internet access is needed.
    url_or_service:
        The target URL, domain, or service name (e.g.
        ``"https://api.openai.com/v1/chat/completions"``).
    data_sent_description:
        Description of what data will leave the system.
    precautions:
        Privacy safeguards and security measures the agent commits to.

    Returns
    -------
    InternetRequest
        The newly created request with ``status="pending"``.
    """
    request = InternetRequest(
        agent_name=agent_name,
        purpose=purpose,
        url_or_service=url_or_service,
        data_sent_description=data_sent_description,
        precautions=precautions,
        status="pending",
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    logger.info(
        "Internet access request #%d created by '%s' for '%s' — awaiting approval.",
        request.id,
        agent_name,
        url_or_service,
    )
    return request


# ---------------------------------------------------------------------------
# Approval / denial
# ---------------------------------------------------------------------------


def approve_request(db: Session, request_id: int) -> InternetRequest:
    """Mark an internet-access request as **approved**.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    request_id:
        Primary key of the :class:`InternetRequest` to approve.

    Returns
    -------
    InternetRequest
        The updated request with ``status="approved"``.

    Raises
    ------
    ValueError
        If the request does not exist or is not in ``"pending"`` status.
    """
    request = db.query(InternetRequest).filter(InternetRequest.id == request_id).first()
    if request is None:
        raise ValueError(f"Internet request #{request_id} not found.")
    if request.status != "pending":
        raise ValueError(
            f"Internet request #{request_id} cannot be approved — "
            f"current status is '{request.status}'."
        )

    request.status = "approved"
    request.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(request)
    logger.info("Internet access request #%d approved.", request_id)
    return request


def deny_request(db: Session, request_id: int) -> InternetRequest:
    """Mark an internet-access request as **denied**.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    request_id:
        Primary key of the :class:`InternetRequest` to deny.

    Returns
    -------
    InternetRequest
        The updated request with ``status="denied"``.

    Raises
    ------
    ValueError
        If the request does not exist or is not in ``"pending"`` status.
    """
    request = db.query(InternetRequest).filter(InternetRequest.id == request_id).first()
    if request is None:
        raise ValueError(f"Internet request #{request_id} not found.")
    if request.status != "pending":
        raise ValueError(
            f"Internet request #{request_id} cannot be denied — "
            f"current status is '{request.status}'."
        )

    request.status = "denied"
    request.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(request)
    logger.info("Internet access request #%d denied.", request_id)
    return request


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def get_pending_requests(db: Session) -> List[InternetRequest]:
    """Return all internet-access requests that are still awaiting user review.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.

    Returns
    -------
    list[InternetRequest]
        Pending requests ordered by creation time (oldest first).
    """
    return (
        db.query(InternetRequest)
        .filter(InternetRequest.status == "pending")
        .order_by(InternetRequest.created_at.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def execute_approved_request(
    db: Session,
    request_id: int,
    executor_func: Callable[[], Any],
) -> Dict[str, Any]:
    """Execute the internet operation *only if* the request is approved.

    The caller provides an *executor_func* (a zero-argument callable) that
    performs the actual network I/O.  The guard verifies that the request
    has been explicitly approved before invoking it, and stores the result
    (or error) back on the request row.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    request_id:
        Primary key of the :class:`InternetRequest`.
    executor_func:
        A callable that performs the network operation and returns a
        JSON-serialisable result.

    Returns
    -------
    dict
        ``{"success": True, "result": <return value>}`` on success, or
        ``{"success": False, "error": "<message>"}`` on failure.

    Raises
    ------
    PermissionError
        If the request is not in ``"approved"`` status.
    ValueError
        If the request does not exist.
    """
    request = db.query(InternetRequest).filter(InternetRequest.id == request_id).first()
    if request is None:
        raise ValueError(f"Internet request #{request_id} not found.")
    if request.status != "approved":
        raise PermissionError(
            f"Internet request #{request_id} is not approved — "
            f"current status is '{request.status}'. "
            "The AI cannot access the internet without explicit user approval."
        )

    try:
        result = executor_func()
        request.status = "executed"
        request.result = {"success": True, "result": result}
        request.data_received_description = (
            f"Execution completed successfully. Result type: {type(result).__name__}"
        )
        db.commit()
        db.refresh(request)
        logger.info("Internet access request #%d executed successfully.", request_id)
        return {"success": True, "result": result}

    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        request.status = "executed"
        request.result = {"success": False, "error": error_message}
        request.data_received_description = (
            f"Execution failed with error: {error_message}"
        )
        db.commit()
        db.refresh(request)
        logger.error(
            "Internet access request #%d failed: %s\n%s",
            request_id,
            error_message,
            traceback.format_exc(),
        )
        return {"success": False, "error": error_message}


# ---------------------------------------------------------------------------
# Human-readable formatting
# ---------------------------------------------------------------------------


def format_request_for_user(request: InternetRequest) -> str:
    """Format an internet-access request as a clear, human-readable string.

    This is intended for display in the chat interface or dashboard so the
    user can make an informed approve/deny decision.

    Parameters
    ----------
    request:
        The :class:`InternetRequest` instance to format.

    Returns
    -------
    str
        Multi-line description covering the agent, purpose, target,
        data handling, precautions, and current status.
    """
    divider = "-" * 60

    lines = [
        divider,
        f"  INTERNET ACCESS REQUEST  #{request.id}",
        divider,
        "",
        f"Agent:        {request.agent_name}",
        f"Status:       {request.status.upper()}",
        f"Requested at: {request.created_at:%Y-%m-%d %H:%M:%S UTC}"
        if request.created_at
        else "Requested at: N/A",
        "",
        "PURPOSE:",
        f"  {request.purpose}",
        "",
        "TARGET:",
        f"  {request.url_or_service}",
        "",
        "DATA THAT WILL BE SENT:",
        f"  {request.data_sent_description or 'No data will be sent.'}",
        "",
        "PRECAUTIONS:",
        f"  {request.precautions or 'None specified.'}",
    ]

    if request.data_received_description:
        lines.extend([
            "",
            "DATA RECEIVED:",
            f"  {request.data_received_description}",
        ])

    if request.resolved_at:
        lines.extend([
            "",
            f"Resolved at:  {request.resolved_at:%Y-%m-%d %H:%M:%S UTC}",
        ])

    lines.append(divider)
    return "\n".join(lines)
