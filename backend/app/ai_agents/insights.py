"""
Agent insight recorder.

Turns an agent/workflow's raw result into a short PLAIN-ENGLISH brief (via
Claude, with a deterministic fallback), saves it as an AgentInsight tagged to
the dashboard section it belongs to, and — where it maps cleanly — persists
native records (content ideas -> Content Studio items, KPIs -> Metrics) so
output shows up where the user expects it. Never surfaces raw JSON to the user.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from backend.app.database import models, crud
from backend.app.utils.logging import OmuraLogger

_logger = OmuraLogger("insights")

# Which dashboard section each agent's output belongs to.
SECTION_BY_AGENT = {
    "inbox": "communication",
    "crm": "business",
    "finance": "business",
    "project": "business",
    "content": "content",
    "health": "health",
    "market": "business",
    "scenario": "scenarios",
    "automation": "automation",
    "outreach": "business",
    "tutor": "titan",
}


def _inner(result: Any) -> Any:
    """Unwrap the {agent, action, result} envelope if present."""
    if isinstance(result, dict) and "result" in result and len(result) <= 4:
        return result["result"]
    return result


def english_summary(agent: str, action: str, result: Any) -> str:
    """Produce a 2-4 sentence plain-English brief of an agent result."""
    from backend.app.ai_agents._claude_caller import call_claude

    raw = json.dumps(result, default=str)[:4000]
    system = (
        "You convert an AI agent's raw output into a short, plain-English brief for a busy "
        "founder named Damarley. Rules: write 2-4 sentences OR up to 4 short bullet lines; "
        "no JSON, no field names, no code, no jargon; lead with the takeaway. If the result is "
        "empty or clearly placeholder/mock data, say so plainly in one line."
    )
    prompt = f"The '{agent}' agent ran '{action}'. Raw result:\n{raw}\n\nWrite the plain-English brief."
    out = call_claude(prompt, system, agent_name="insights", temperature=0.3, max_tokens=350)
    return (out or "").strip() or _humanize(_inner(result))


def _humanize(value: Any, depth: int = 0) -> str:
    """Deterministic fallback: render a value as readable text (no JSON syntax)."""
    pad = "  " * depth
    if value is None or value == "" or value == [] or value == {}:
        return "No output was returned."
    if isinstance(value, (str, int, float, bool)):
        return f"{value}"
    if isinstance(value, list):
        lines = []
        for item in value[:8]:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}- {_humanize(item, depth + 1)}")
            else:
                lines.append(f"{pad}- {item}")
        return "\n".join(lines)
    if isinstance(value, dict):
        lines = []
        for k, v in list(value.items())[:12]:
            label = str(k).replace("_", " ").capitalize()
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}{label}:\n{_humanize(v, depth + 1)}")
            else:
                lines.append(f"{pad}{label}: {v}")
        return "\n".join(lines)
    return str(value)


def _native_persist(db: Session, agent: str, action: str, result: Any) -> None:
    """Best-effort: write outputs into their real tables where the shape is clear."""
    inner = _inner(result)
    try:
        # Content AI ideas -> real Content Studio items (status: idea)
        if agent == "content" and action == "suggest_content_ideas":
            ideas = inner if isinstance(inner, list) else (
                inner.get("items") or inner.get("ideas") or [] if isinstance(inner, dict) else []
            )
            for idea in ideas[:10]:
                if isinstance(idea, dict):
                    title = idea.get("title") or idea.get("idea") or idea.get("topic") or "Content idea"
                    body = idea.get("description") or idea.get("hook") or json.dumps(idea, default=str)
                else:
                    title, body = str(idea), str(idea)
                crud.create_record(db, models.ContentItem, title=str(title)[:500], body=str(body), status="idea")

        # Finance KPIs -> real Metrics on Business Command
        elif agent == "finance" and action == "calculate_kpis":
            kpis = inner.get("kpis") if isinstance(inner, dict) else None
            if isinstance(kpis, dict):
                for name, val in list(kpis.items())[:12]:
                    if isinstance(val, (int, float)):
                        crud.create_record(db, models.Metric, category="kpi",
                                           name=str(name).replace("_", " ").title(), value=float(val),
                                           unit="", source="finance_ai")
    except Exception as exc:  # native persistence must never break the run
        _logger.warning(f"native persist skipped for {agent}.{action}: {exc}")


def humanize_brief(agent: str, action: str, result: Any) -> str:
    """Instant, LLM-free English-ish brief for the request path (never hangs)."""
    body = _humanize(_inner(result))
    head = f"{agent.replace('_', ' ').title()} · {action.replace('_', ' ')}"
    return f"{head}\n{body}"[:1500]


def record_agent_insight_bg(agent: str, action: str, result: Any) -> None:
    """Background entry point — opens its own DB session (the request's is closed
    by the time this runs) and records the polished insight off the hot path."""
    from backend.app.database.session import SessionLocal
    db = SessionLocal()
    try:
        record_agent_insight(db, agent, action, result)
    except Exception as exc:
        _logger.warning(f"background insight failed for {agent}.{action}: {exc}")
    finally:
        db.close()


def record_agent_insight(db: Session, agent: str, action: str, result: Any) -> str:
    """Summarize -> persist insight -> native-persist. Returns the English summary."""
    section = SECTION_BY_AGENT.get(agent, "automation")
    summary = english_summary(agent, action, result)
    title = f"{agent.replace('_', ' ').title()} · {action.replace('_', ' ')}"
    try:
        crud.create_record(
            db, models.AgentInsight,
            agent_name=agent, action=action, section=section,
            title=title[:255], summary=summary,
        )
    except Exception as exc:
        _logger.warning(f"insight save failed for {agent}.{action}: {exc}")
    _native_persist(db, agent, action, result)
    return summary
