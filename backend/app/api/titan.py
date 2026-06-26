"""
Titan Track API router.

Mounted at /api/titan (+ /api/dashboard/titan-track) from main.py via
``app.include_router(titan.router)``. Follows the existing /api/{resource}
conventions: thin endpoints over crud + the TutorAI agent, with the mastery
gate enforced server-side (never by self-report).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.database import crud
from backend.app.database.models import (
    LearningTrack, LearningModule, MasteryEntry, LeadershipRep,
    StreakLog, DailySession, RoadmapSnapshot, SessionFeedback,
    Lead, Communication, CalendarEvent, LeadStatus,
    LessonSchedulePreference, ModuleProject, NegotiationSession, ProgressTest,
)
from backend.app.ai_agents.tutor_agent import TutorAI, QUIZ_PASS_THRESHOLD

router = APIRouter(prefix="/api/titan", tags=["titan"])


# ── Request schemas ─────────────────────────────────────────────────

class ModuleUpdate(BaseModel):
    status: Optional[str] = None
    order_index: Optional[int] = None
    culminating_artifact: Optional[str] = None


class AttemptRequest(BaseModel):
    answers: List[int]


class ExplainBackRequest(BaseModel):
    transcript: str
    prior_attempts: Optional[int] = 0


class ReflectRequest(BaseModel):
    reflection: str
    avoided_moments: Optional[str] = None


class SessionStartRequest(BaseModel):
    energy_level: Optional[str] = None  # low | med | high


class SessionCompleteRequest(BaseModel):
    minutes_spent: Optional[int] = 0


class FeedbackRequest(BaseModel):
    module_id: Optional[int] = None
    thumbs: str  # up | down
    note: Optional[str] = None


class SnapshotRequest(BaseModel):
    change_note: Optional[str] = ""
    compass_note: Optional[str] = None


class SlotPref(BaseModel):
    slot: str  # morning | afternoon | evening
    time: str  # "08:00"
    track_pref: Optional[str] = None  # A | B | C | D | E


class SchedulePrefRequest(BaseModel):
    slots: List[SlotPref]


class ProjectProgressRequest(BaseModel):
    completed_steps: List[int]


class ProjectSubmitRequest(BaseModel):
    submission_text: str


class NegotiationStartRequest(BaseModel):
    module_id: Optional[int] = None
    scenario_type: Optional[str] = None


class NegotiationRespondRequest(BaseModel):
    message: str


class TestGenerateRequest(BaseModel):
    type: str = "weekly"  # weekly | monthly


class TestSubmitRequest(BaseModel):
    answers: List[int]


class StreakCheckinRequest(BaseModel):
    module_id: Optional[int] = None
    minutes: Optional[int] = 0


# ── Defaults / helpers for the v2 (Duolingo-style) layer ─────────────

DEFAULT_SLOTS = [
    {"slot": "morning", "time": "08:00", "track_pref": "A"},
    {"slot": "afternoon", "time": "13:00", "track_pref": "C"},
    {"slot": "evening", "time": "19:00", "track_pref": "E"},
]


def _pick_module_for_track(db: Session, track_code: Optional[str]) -> Optional[LearningModule]:
    """Pick the lesson module for a slot: the in-progress module in the
    preferred track, else the first available one. Falls back across now-tier
    tracks if the preferred track has nothing actionable."""
    def _query(code: Optional[str], status: str):
        q = (
            db.query(LearningModule)
            .join(LearningTrack, LearningModule.track_id == LearningTrack.id)
            .filter(LearningModule.tier == "now", LearningModule.status == status)
        )
        if code:
            q = q.filter(LearningTrack.code == code)
        return q.order_by(LearningTrack.order_index, LearningModule.order_index).first()

    return (
        _query(track_code, "in_progress")
        or _query(track_code, "available")
        or _query(None, "in_progress")
        or _query(None, "available")
    )


def _get_or_create_project(db: Session, module: LearningModule) -> ModuleProject:
    """Return the module's project, generating its brief from the cached lesson
    content the first time it is requested."""
    proj = db.query(ModuleProject).filter(ModuleProject.module_id == module.id).first()
    if proj:
        return proj
    tutor = TutorAI(db)
    content = tutor.generate_module_content(module.id)
    brief = (content or {}).get("project_brief") or tutor._fallback_project(module)
    proj = ModuleProject(module_id=module.id, brief=brief, completed_steps=[], status="available")
    db.add(proj)
    try:
        db.commit()
        db.refresh(proj)
    except IntegrityError:
        # Race: a concurrent request already created this module's project.
        db.rollback()
        proj = db.query(ModuleProject).filter(ModuleProject.module_id == module.id).first()
    return proj


def _project_public(db: Session, p: ModuleProject) -> Dict[str, Any]:
    d = _serialize(p)
    m = db.query(LearningModule).filter(LearningModule.id == p.module_id).first()
    if m:
        tr = db.query(LearningTrack).filter(LearningTrack.id == m.track_id).first()
        d["module_title"] = m.title
        d["track_code"] = tr.code if tr else None
        d["track_name"] = tr.name if tr else None
        d["color_theme"] = tr.color_theme if tr else "#3B82F6"
    return d


def _test_public(t: ProgressTest, reveal: bool = False) -> Dict[str, Any]:
    """Test dict for the client. Hides the correct index + explanation until the
    test has been submitted (``reveal``)."""
    questions = []
    for q in (t.questions or []):
        pub = {
            "question": q.get("question"),
            "options": q.get("options", []),
            "module_id": q.get("module_id"),
            "track_code": q.get("track_code"),
        }
        if reveal:
            pub["correct"] = q.get("correct")
            pub["explanation"] = q.get("explanation")
        questions.append(pub)
    return {
        "id": t.id,
        "type": t.type,
        "period_start": t.period_start,
        "period_end": t.period_end,
        "questions": questions,
        "submitted_at": t.submitted_at.isoformat() if t.submitted_at else None,
        "score_overall": t.score_overall,
        "scores_by_track": t.scores_by_track,
        "answers": t.answers,
    }


# ── Serialization ───────────────────────────────────────────────────

def _serialize(record: Any) -> Dict[str, Any]:
    if record is None:
        return {}
    out: Dict[str, Any] = {}
    for col in record.__table__.columns:
        val = getattr(record, col.name, None)
        out[col.name] = val.isoformat() if isinstance(val, datetime) else val
    return out


def _module_public(m: LearningModule) -> Dict[str, Any]:
    """Module dict for the API — never leaks the cached quiz answer key."""
    d = _serialize(m)
    d.pop("extra_data", None)  # may contain generated_content + answer key
    return d


# ── Progress recomputation + gate ───────────────────────────────────

def _recompute_track_progress(db: Session, track_id: int) -> float:
    modules = db.query(LearningModule).filter(
        LearningModule.track_id == track_id, LearningModule.tier == "now"
    ).all()
    if not modules:
        return 0.0
    mastered = sum(1 for m in modules if m.status == "mastered")
    pct = round((mastered / len(modules)) * 100, 1)
    track = db.query(LearningTrack).filter(LearningTrack.id == track_id).first()
    if track:
        track.progress_pct = pct
        db.commit()
    return pct


def _unlock_dependents(db: Session) -> List[int]:
    """Flip any locked module whose prerequisites are now all mastered to
    'available'. Returns the ids that were unlocked."""
    unlocked: List[int] = []
    mastered_ids = {
        m.id for m in db.query(LearningModule).filter(LearningModule.status == "mastered").all()
    }
    candidates = db.query(LearningModule).filter(LearningModule.status == "locked").all()
    for m in candidates:
        prereqs = m.prerequisite_ids or []
        if prereqs and all(pid in mastered_ids for pid in prereqs):
            m.status = "available"
            unlocked.append(m.id)
    if unlocked:
        db.commit()
    return unlocked


# ══════════════════════════════════════════════════════════════════
# Tracks & Modules
# ══════════════════════════════════════════════════════════════════

@router.get("/tracks")
def list_tracks(db: Session = Depends(get_db)):
    tracks = db.query(LearningTrack).order_by(LearningTrack.order_index).all()
    result = []
    for t in tracks:
        modules = db.query(LearningModule).filter(LearningModule.track_id == t.id).all()
        d = _serialize(t)
        d["module_count"] = len(modules)
        d["mastered_count"] = sum(1 for m in modules if m.status == "mastered")
        current = next((m for m in sorted(modules, key=lambda x: x.order_index)
                        if m.status == "in_progress"), None)
        nxt = next((m for m in sorted(modules, key=lambda x: x.order_index)
                    if m.status in ("available", "locked")), None)
        d["current_module"] = _module_public(current) if current else None
        d["next_module"] = _module_public(nxt) if nxt else None
        result.append(d)
    return result


@router.get("/modules")
def list_modules(
    track_id: Optional[int] = None,
    tier: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(LearningModule)
    if track_id is not None:
        query = query.filter(LearningModule.track_id == track_id)
    if tier:
        query = query.filter(LearningModule.tier == tier)
    if status:
        query = query.filter(LearningModule.status == status)
    modules = query.order_by(LearningModule.track_id, LearningModule.order_index).all()
    return [_module_public(m) for m in modules]


@router.get("/modules/{module_id}")
def get_module(module_id: int, db: Session = Depends(get_db)):
    m = db.query(LearningModule).filter(LearningModule.id == module_id).first()
    if not m:
        raise HTTPException(404, "Module not found")
    d = _module_public(m)
    prereqs = m.prerequisite_ids or []
    d["prerequisite_chain"] = [
        _module_public(p) for p in
        db.query(LearningModule).filter(LearningModule.id.in_(prereqs)).all()
    ] if prereqs else []
    return d


@router.patch("/modules/{module_id}")
def update_module(module_id: int, data: ModuleUpdate, db: Session = Depends(get_db)):
    m = db.query(LearningModule).filter(LearningModule.id == module_id).first()
    if not m:
        raise HTTPException(404, "Module not found")
    updates = data.model_dump(exclude_none=True)
    # Guardrail: the gate cannot be cleared by manual self-report. 'mastered'
    # is reachable only through the explain-back endpoint after a passing quiz.
    if updates.get("status") == "mastered":
        raise HTTPException(
            400, "A module cannot be marked mastered manually — it must pass the quiz + explain-back gate."
        )
    for k, v in updates.items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return _module_public(m)


# ══════════════════════════════════════════════════════════════════
# Mastery & Gating
# ══════════════════════════════════════════════════════════════════

def _latest_attempt(db: Session, module_id: int) -> Optional[MasteryEntry]:
    return (
        db.query(MasteryEntry)
        .filter(MasteryEntry.module_id == module_id)
        .order_by(desc(MasteryEntry.attempt_number))
        .first()
    )


@router.post("/modules/{module_id}/attempt")
def submit_attempt(module_id: int, data: AttemptRequest, db: Session = Depends(get_db)):
    m = db.query(LearningModule).filter(LearningModule.id == module_id).first()
    if not m:
        raise HTTPException(404, "Module not found")
    if m.status == "locked":
        raise HTTPException(409, "Module is locked — clear its prerequisites first.")

    tutor = TutorAI(db)
    grade = tutor.grade_module_attempt(module_id, data.answers)
    if "error" in grade:
        raise HTTPException(400, grade["error"])

    prev = _latest_attempt(db, module_id)
    attempt_number = (prev.attempt_number + 1) if prev else 1
    entry = MasteryEntry(
        module_id=module_id,
        attempt_number=attempt_number,
        quiz_score=grade["score"],
        quiz_answers={"answers": data.answers},
        explain_back_passed=False,
        passed=False,
        ai_feedback=grade["feedback"],
    )
    db.add(entry)
    if m.status == "available":
        m.status = "in_progress"
    db.commit()
    db.refresh(entry)

    crud.log_agent_action(db, "tutor", "grade_module_attempt",
                          {"module_id": module_id}, grade, "success")
    return {
        "mastery_entry_id": entry.id,
        "attempt_number": attempt_number,
        **grade,
        "next_step": ("explain_back" if grade.get("passed_quiz") else "retry_quiz"),
    }


@router.post("/modules/{module_id}/explain-back")
def submit_explain_back(module_id: int, data: ExplainBackRequest, db: Session = Depends(get_db)):
    m = db.query(LearningModule).filter(LearningModule.id == module_id).first()
    if not m:
        raise HTTPException(404, "Module not found")

    latest = _latest_attempt(db, module_id)
    if not latest or latest.quiz_score < QUIZ_PASS_THRESHOLD:
        raise HTTPException(
            409,
            f"Pass the quiz (>= {QUIZ_PASS_THRESHOLD}%) before the explain-back gate.",
        )

    tutor = TutorAI(db)
    verdict = tutor.run_explain_back_check(module_id, data.transcript, data.prior_attempts or 0)
    if "error" in verdict:
        raise HTTPException(400, verdict["error"])

    latest.explain_back_transcript = data.transcript
    latest.explain_back_passed = bool(verdict.get("passed"))
    latest.ai_feedback = (latest.ai_feedback or "") + "\n\nExplain-back: " + str(verdict.get("feedback", ""))

    unlocked: List[int] = []
    mastered = False
    if latest.explain_back_passed and latest.quiz_score >= QUIZ_PASS_THRESHOLD:
        latest.passed = True
        m.status = "mastered"
        mastered = True
        db.commit()
        _recompute_track_progress(db, m.track_id)
        unlocked = _unlock_dependents(db)
    else:
        db.commit()

    crud.log_agent_action(db, "tutor", "run_explain_back_check",
                          {"module_id": module_id}, verdict, "success")
    return {
        **verdict,
        "module_mastered": mastered,
        "unlocked_module_ids": unlocked,
    }


@router.get("/modules/{module_id}/mastery-history")
def mastery_history(module_id: int, db: Session = Depends(get_db)):
    entries = (
        db.query(MasteryEntry)
        .filter(MasteryEntry.module_id == module_id)
        .order_by(MasteryEntry.attempt_number)
        .all()
    )
    return [_serialize(e) for e in entries]


# ══════════════════════════════════════════════════════════════════
# Leadership Reps
# ══════════════════════════════════════════════════════════════════

@router.get("/reps")
def list_reps(days: int = 30, db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    reps = (
        db.query(LeadershipRep)
        .filter(LeadershipRep.date >= since)
        .order_by(desc(LeadershipRep.date))
        .all()
    )
    return [_serialize(r) for r in reps]


@router.get("/reps/{rep_id}")
def get_rep(rep_id: int, db: Session = Depends(get_db)):
    r = db.query(LeadershipRep).filter(LeadershipRep.id == rep_id).first()
    if not r:
        raise HTTPException(404, "Rep not found")
    return _serialize(r)


@router.post("/reps/{rep_id}/reflect")
def reflect_on_rep(rep_id: int, data: ReflectRequest, db: Session = Depends(get_db)):
    r = db.query(LeadershipRep).filter(LeadershipRep.id == rep_id).first()
    if not r:
        raise HTTPException(404, "Rep not found")
    r.user_reflection = data.reflection
    if data.avoided_moments:
        r.avoided_moments = data.avoided_moments
    db.commit()
    db.refresh(r)
    return _serialize(r)


@router.post("/reps/sync")
def sync_reps(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    """Pull new leadership reps from Lead / Communication / CalendarEvent
    records that look like calls, pitches, or negotiations, and generate an
    AI after-action review for each. Idempotent on (source_table, id).

    Bounded by ``limit`` (default 10) because each new rep triggers a synchronous
    LLM after-action review — an unbounded loop would risk a request timeout.
    Re-call to process the next batch.
    """
    tutor = TutorAI(db)
    created = 0

    def _already(table: str, rid: int) -> bool:
        return db.query(LeadershipRep).filter(
            LeadershipRep.source_table == table,
            LeadershipRep.source_record_id == rid,
        ).first() is not None

    # Leads that have progressed past first contact = real reps happened.
    leads = db.query(Lead).filter(Lead.status.in_([
        LeadStatus.CONTACTED, LeadStatus.QUALIFIED, LeadStatus.PROPOSAL, LeadStatus.WON,
    ])).all()
    for lead in leads:
        if created >= limit:
            break
        if _already("leads", lead.id):
            continue
        desc_text = f"{lead.status} interaction with {lead.name}" + (f" ({lead.company})" if lead.company else "")
        if lead.notes:
            desc_text += f". Notes: {lead.notes[:400]}"
        review = tutor.generate_leadership_rep_review(desc_text, source_type="lead_call")
        rep = LeadershipRep(
            source_type="lead_call", source_table="leads", source_record_id=lead.id,
            date=lead.last_contact or lead.updated_at or datetime.utcnow(),
            description=desc_text,
            ai_after_action_review=review.get("after_action_review"),
            presence_score=review.get("presence_score"),
            avoided_moments=review.get("avoided_moments"),
        )
        db.add(rep)
        created += 1

    # Calendar events that read like pitches / calls / negotiations.
    keywords = ("pitch", "call", "negotiat", "demo", "meeting", "presentation")
    events = db.query(CalendarEvent).filter(CalendarEvent.start_time <= datetime.utcnow()).all()
    for ev in events:
        if created >= limit:
            break
        title = (ev.title or "").lower()
        if not any(k in title for k in keywords):
            continue
        if _already("calendar_events", ev.id):
            continue
        desc_text = f"{ev.title}" + (f" — {ev.description[:300]}" if ev.description else "")
        review = tutor.generate_leadership_rep_review(desc_text, source_type="pitch")
        rep = LeadershipRep(
            source_type="pitch", source_table="calendar_events", source_record_id=ev.id,
            date=ev.start_time or datetime.utcnow(), description=desc_text,
            ai_after_action_review=review.get("after_action_review"),
            presence_score=review.get("presence_score"),
            avoided_moments=review.get("avoided_moments"),
        )
        db.add(rep)
        created += 1

    db.commit()
    crud.log_agent_action(db, "tutor", "sync_reps", {}, {"created": created}, "success")
    return {"created": created}


# ══════════════════════════════════════════════════════════════════
# Daily Session
# ══════════════════════════════════════════════════════════════════

@router.get("/session/today")
def session_today(energy_level: Optional[str] = None, db: Session = Depends(get_db)):
    tutor = TutorAI(db)
    return tutor.get_daily_session(energy_level)


@router.post("/session/{session_id}/start")
def start_session(session_id: int, data: SessionStartRequest, db: Session = Depends(get_db)):
    s = db.query(DailySession).filter(DailySession.id == session_id).first()
    if not s:
        raise HTTPException(404, "Session not found")
    s.started = True
    if data.energy_level:
        s.energy_level_reported = data.energy_level
    db.commit()
    return {"started": True, "session_id": session_id}


@router.post("/session/{session_id}/complete")
def complete_session(session_id: int, data: SessionCompleteRequest, db: Session = Depends(get_db)):
    s = db.query(DailySession).filter(DailySession.id == session_id).first()
    if not s:
        raise HTTPException(404, "Session not found")
    if s.completed:
        # Idempotent: completing twice must not double-count minutes or re-streak.
        return {"completed": True, "session_id": session_id,
                "already_completed": True, "streak": _streak_summary(db)}
    s.completed = True
    s.actual_minutes_spent = (s.actual_minutes_spent or 0) + (data.minutes_spent or 0)
    db.commit()
    streak = _update_streak(db, s)
    return {"completed": True, "session_id": session_id, "streak": streak}


# ── Streak ──────────────────────────────────────────────────────────

def _mark_day_active(db: Session, track_ids: Optional[List[int]] = None,
                     minutes: int = 0) -> Dict[str, Any]:
    """Mark today as a chain-intact day (idempotent). Used by both the daily-
    session completion and the lighter per-lesson 'check-in'."""
    track_ids = track_ids or []
    today = datetime.utcnow().strftime("%Y-%m-%d")
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    log = db.query(StreakLog).filter(StreakLog.date == today).first()
    prev = db.query(StreakLog).filter(StreakLog.date == yesterday).first()
    prev_streak = _current_streak_length(db, yesterday) if prev and prev.chain_intact else 0
    new_len = prev_streak + 1

    def _merge(into: StreakLog) -> None:
        touched = set(into.tracks_touched or []) | set(track_ids)
        into.tracks_touched = list(touched)
        into.total_minutes = (into.total_minutes or 0) + (minutes or 0)
        into.chain_intact = True
        into.longest_streak_at_time = max(into.longest_streak_at_time or 0, new_len)

    if log:
        _merge(log)
        db.commit()
    else:
        log = StreakLog(
            date=today, tracks_touched=list(track_ids),
            total_minutes=minutes or 0,
            chain_intact=True, longest_streak_at_time=new_len,
        )
        db.add(log)
        try:
            db.commit()
        except IntegrityError:
            # Race: a concurrent first-of-day write won (StreakLog.date is unique).
            # Roll back and merge into the row that landed instead of 500-ing.
            db.rollback()
            won = db.query(StreakLog).filter(StreakLog.date == today).first()
            if won:
                _merge(won)
                db.commit()
    return _streak_summary(db)


def _update_streak(db: Session, session: DailySession) -> Dict[str, Any]:
    track_ids: List[int] = []
    for mid in (session.modules_assigned or []):
        m = db.query(LearningModule).filter(LearningModule.id == mid).first()
        if m and m.track_id not in track_ids:
            track_ids.append(m.track_id)
    return _mark_day_active(db, track_ids, session.actual_minutes_spent or 0)


@router.post("/streak/checkin")
def streak_checkin(data: StreakCheckinRequest, db: Session = Depends(get_db)):
    """Lightweight 'I did work today' signal — keeps the chain alive when the
    learner finishes a lesson, project, or test outside the daily-session flow."""
    track_ids: List[int] = []
    if data.module_id is not None:
        m = db.query(LearningModule).filter(LearningModule.id == data.module_id).first()
        if m:
            track_ids.append(m.track_id)
    return _mark_day_active(db, track_ids, data.minutes or 0)


def _current_streak_length(db: Session, end_date: str) -> int:
    """Count consecutive chain-intact days ending at end_date (inclusive)."""
    length = 0
    cursor = datetime.strptime(end_date, "%Y-%m-%d")
    while True:
        d = cursor.strftime("%Y-%m-%d")
        log = db.query(StreakLog).filter(StreakLog.date == d, StreakLog.chain_intact == True).first()  # noqa: E712
        if not log:
            break
        length += 1
        cursor -= timedelta(days=1)
    return length


def _streak_summary(db: Session) -> Dict[str, Any]:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    current = _current_streak_length(db, today)
    longest = db.query(StreakLog).order_by(desc(StreakLog.longest_streak_at_time)).first()
    longest_val = max(current, longest.longest_streak_at_time if longest else 0)

    # 26-week heatmap (GitHub-style) — one cell per day.
    cells = []
    start = datetime.utcnow() - timedelta(days=181)
    logs = {l.date: l for l in db.query(StreakLog).all()}
    for i in range(182):
        d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        log = logs.get(d)
        cells.append({
            "date": d,
            "active": bool(log and log.chain_intact),
            "minutes": (log.total_minutes if log else 0),
            "tracks": (log.tracks_touched if log else []),
        })
    return {"current_streak": current, "longest_streak": longest_val, "heatmap": cells}


@router.get("/streak")
def get_streak(db: Session = Depends(get_db)):
    return _streak_summary(db)


# ══════════════════════════════════════════════════════════════════
# Session feedback (QA Layer 4)
# ══════════════════════════════════════════════════════════════════

@router.post("/session/{session_id}/feedback")
def session_feedback(session_id: int, data: FeedbackRequest, db: Session = Depends(get_db)):
    if data.thumbs not in ("up", "down"):
        raise HTTPException(400, "thumbs must be 'up' or 'down'")
    s = db.query(DailySession).filter(DailySession.id == session_id).first()
    if not s:
        raise HTTPException(404, "Session not found")

    triggered = False
    if data.thumbs == "down" and data.module_id is not None:
        recent_downs = (
            db.query(SessionFeedback)
            .filter(SessionFeedback.module_id == data.module_id, SessionFeedback.thumbs == "down")
            .order_by(desc(SessionFeedback.created_at))
            .limit(1)
            .all()
        )
        # This down + one prior down = two consecutive -> regenerate with a different approach.
        if recent_downs:
            triggered = True
            TutorAI(db).generate_module_content(data.module_id, force=True)

    fb = SessionFeedback(
        session_id=session_id, module_id=data.module_id,
        thumbs=data.thumbs, note=data.note, triggered_regeneration=triggered,
    )
    db.add(fb)
    db.commit()
    return {"logged": True, "triggered_regeneration": triggered}


# ══════════════════════════════════════════════════════════════════
# Roadmap
# ══════════════════════════════════════════════════════════════════

@router.get("/roadmap")
def get_roadmap(db: Session = Depends(get_db)):
    tracks = db.query(LearningTrack).order_by(LearningTrack.order_index).all()
    now_tracks, horizon_tracks = [], []
    for t in tracks:
        modules = db.query(LearningModule).filter(
            LearningModule.track_id == t.id
        ).order_by(LearningModule.order_index).all()
        entry = {**_serialize(t), "modules": [_module_public(m) for m in modules]}
        (horizon_tracks if t.target_tier == "horizon" else now_tracks).append(entry)
    latest_snapshot = db.query(RoadmapSnapshot).order_by(desc(RoadmapSnapshot.version)).first()
    return {
        "now": now_tracks,
        "horizon": horizon_tracks,
        "compass_note": latest_snapshot.compass_note if latest_snapshot else None,
        "version": latest_snapshot.version if latest_snapshot else 0,
    }


@router.post("/roadmap/snapshot")
def save_snapshot(data: SnapshotRequest, db: Session = Depends(get_db)):
    last = db.query(RoadmapSnapshot).order_by(desc(RoadmapSnapshot.version)).first()
    version = (last.version + 1) if last else 1
    full = get_roadmap(db)
    snap = RoadmapSnapshot(
        version=version, full_roadmap_json=full,
        change_note=data.change_note,
        compass_note=data.compass_note if data.compass_note is not None else (last.compass_note if last else None),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return _serialize(snap)


@router.get("/roadmap/history")
def roadmap_history(db: Session = Depends(get_db)):
    snaps = db.query(RoadmapSnapshot).order_by(desc(RoadmapSnapshot.version)).all()
    return [
        {"id": s.id, "version": s.version, "change_note": s.change_note,
         "compass_note": s.compass_note,
         "created_at": s.created_at.isoformat() if s.created_at else None}
        for s in snaps
    ]


# ══════════════════════════════════════════════════════════════════
# Lesson content (full Robert-Greene-style lesson for one module)
# ══════════════════════════════════════════════════════════════════

@router.get("/modules/{module_id}/lesson")
def get_module_lesson(module_id: int, db: Session = Depends(get_db)):
    """Full lesson content for a module: big picture, concept, historical
    example, modern practice, diagram, exercises, quiz (no answer key),
    explain-back prompt, and the project brief. Used by the Lesson view."""
    m = db.query(LearningModule).filter(LearningModule.id == module_id).first()
    if not m:
        raise HTTPException(404, "Module not found")
    tutor = TutorAI(db)
    content = tutor.generate_module_content(module_id)
    if isinstance(content, dict) and "error" in content:
        raise HTTPException(400, content["error"])
    latest = _latest_attempt(db, module_id)
    return {
        "module": tutor._module_summary(m),
        "content": tutor._public_content(content),
        "quiz_passed": bool(latest and latest.quiz_score >= QUIZ_PASS_THRESHOLD),
        "mastered": m.status == "mastered",
    }


@router.post("/modules/{module_id}/refresh")
def refresh_module_lesson(module_id: int, db: Session = Depends(get_db)):
    """Opt-in adaptation: ask the AI to re-author THIS one lesson on demand.

    Bounded to your near-term working set — only now-tier modules you can
    currently act on (available / in progress). The AI cannot regenerate future,
    locked, completed, or horizon lessons, so it adjusts what's in front of you
    (~the next couple of weeks) without churning whole courses or jumping ahead.
    """
    m = db.query(LearningModule).filter(LearningModule.id == module_id).first()
    if not m:
        raise HTTPException(404, "Module not found")
    if m.tier != "now" or m.status not in ("available", "in_progress"):
        raise HTTPException(
            409,
            "You can only refresh a lesson you're currently working on — not "
            "future, locked, completed, or horizon lessons.",
        )
    tutor = TutorAI(db)
    content = tutor.generate_module_content(module_id, force=True)  # force = AI re-author
    if isinstance(content, dict) and "error" in content:
        raise HTTPException(400, content["error"])
    crud.log_agent_action(db, "tutor", "refresh_lesson", {"module_id": module_id}, {"ok": True}, "success")
    latest = _latest_attempt(db, module_id)
    return {
        "module": tutor._module_summary(m),
        "content": tutor._public_content(content),
        "quiz_passed": bool(latest and latest.quiz_score >= QUIZ_PASS_THRESHOLD),
        "mastered": m.status == "mastered",
    }


# ══════════════════════════════════════════════════════════════════
# Schedule preferences
# ══════════════════════════════════════════════════════════════════

@router.get("/schedule/preferences")
def get_schedule_prefs(db: Session = Depends(get_db)):
    pref = db.query(LessonSchedulePreference).order_by(desc(LessonSchedulePreference.id)).first()
    return {"slots": (pref.slots if pref and pref.slots else DEFAULT_SLOTS)}


@router.put("/schedule/preferences")
def update_schedule_prefs(data: SchedulePrefRequest, db: Session = Depends(get_db)):
    slots = [s.model_dump() for s in data.slots][:3]  # 2-3 slots/day, 1 hour each
    pref = db.query(LessonSchedulePreference).order_by(desc(LessonSchedulePreference.id)).first()
    if pref:
        pref.slots = slots
    else:
        pref = LessonSchedulePreference(slots=slots)
        db.add(pref)
    db.commit()
    return {"slots": slots}


def _today_lessons(db: Session) -> List[Dict[str, Any]]:
    """Map each scheduled slot to the module the learner should do in it."""
    pref = db.query(LessonSchedulePreference).order_by(desc(LessonSchedulePreference.id)).first()
    slots = (pref.slots if pref and pref.slots else DEFAULT_SLOTS)
    out = []
    for s in slots:
        m = _pick_module_for_track(db, s.get("track_pref"))
        card = {"slot": s.get("slot"), "time": s.get("time"), "track_pref": s.get("track_pref"), "module": None}
        if m:
            tr = db.query(LearningTrack).filter(LearningTrack.id == m.track_id).first()
            card["module"] = {
                "id": m.id, "title": m.title, "status": m.status,
                "track_code": tr.code if tr else None,
                "track_name": tr.name if tr else None,
                "color_theme": tr.color_theme if tr else "#3B82F6",
                "phase_code": m.phase_code,
            }
        out.append(card)
    return out


# ══════════════════════════════════════════════════════════════════
# Projects (build real things)
# ══════════════════════════════════════════════════════════════════

@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    projs = db.query(ModuleProject).order_by(desc(ModuleProject.updated_at)).all()
    return [_project_public(db, p) for p in projs]


@router.post("/modules/{module_id}/project")
def open_module_project(module_id: int, db: Session = Depends(get_db)):
    """Create-or-get the module's project. POST (not GET) because the first call
    lazily materializes the ModuleProject row — a write, so it must not ride a GET."""
    m = db.query(LearningModule).filter(LearningModule.id == module_id).first()
    if not m:
        raise HTTPException(404, "Module not found")
    return _project_public(db, _get_or_create_project(db, m))


@router.get("/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    p = db.query(ModuleProject).filter(ModuleProject.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    return _project_public(db, p)


@router.put("/projects/{project_id}/progress")
def update_project_progress(project_id: int, data: ProjectProgressRequest, db: Session = Depends(get_db)):
    p = db.query(ModuleProject).filter(ModuleProject.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    p.completed_steps = sorted(set(int(i) for i in data.completed_steps))
    if p.status in ("available",) and p.completed_steps:
        p.status = "in_progress"
    db.commit()
    db.refresh(p)
    return _project_public(db, p)


@router.post("/projects/{project_id}/submit")
def submit_project(project_id: int, data: ProjectSubmitRequest, db: Session = Depends(get_db)):
    p = db.query(ModuleProject).filter(ModuleProject.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    m = db.query(LearningModule).filter(LearningModule.id == p.module_id).first()
    if not m:
        raise HTTPException(404, "Module not found")
    submission = (data.submission_text or "").strip()
    if not submission:
        raise HTTPException(400, "Submission is empty.")

    # Idempotent: an identical re-submit of an already-graded project returns the
    # stored grade rather than re-running the grader / re-logging. A genuine
    # revision (changed text) re-grades — that's the intentional revise-and-resubmit.
    if p.status == "graded" and p.ai_feedback and (p.submission_text or "").strip() == submission:
        return {**_project_public(db, p), "grade": p.ai_feedback}

    tutor = TutorAI(db)
    rubric = (p.brief or {}).get("rubric")
    grade = tutor.grade_project_submission(m, data.submission_text, rubric)

    p.submission_text = data.submission_text
    p.submitted_at = datetime.utcnow()
    p.score = grade.get("score")
    p.ai_feedback = grade
    p.status = "graded"
    db.commit()
    db.refresh(p)

    crud.log_agent_action(db, "tutor", "grade_project_submission",
                          {"module_id": m.id, "project_id": p.id},
                          {"score": grade.get("score")}, "success")
    return {**_project_public(db, p), "grade": grade}


@router.get("/projects/{project_id}/feedback")
def project_feedback(project_id: int, db: Session = Depends(get_db)):
    p = db.query(ModuleProject).filter(ModuleProject.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    return {"score": p.score, "ai_feedback": p.ai_feedback, "status": p.status}


# ══════════════════════════════════════════════════════════════════
# Negotiation / leadership simulation
# ══════════════════════════════════════════════════════════════════

def _negotiation_public(s: NegotiationSession) -> Dict[str, Any]:
    # Strip ``_``-prefixed keys (e.g. ``_counterpart_position``) so the learner
    # never sees the counterpart's hidden BATNA — only the counterpart AI and the
    # after-action debrief use it server-side.
    scenario = {k: v for k, v in (s.scenario or {}).items() if not k.startswith("_")}
    return {
        "id": s.id, "module_id": s.module_id, "scenario": scenario,
        "rounds": s.rounds or [], "outcome": s.outcome,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
    }


@router.post("/negotiation/start")
def start_negotiation(data: NegotiationStartRequest, db: Session = Depends(get_db)):
    tutor = TutorAI(db)
    module = None
    if data.module_id is not None:
        module = db.query(LearningModule).filter(LearningModule.id == data.module_id).first()
    scenario = tutor.negotiation_scenario(module, data.scenario_type)
    rounds = [{"role": "counterpart", "text": scenario.get("opening", ""),
               "ts": datetime.utcnow().isoformat()}]
    s = NegotiationSession(module_id=data.module_id, scenario=scenario, rounds=rounds)
    db.add(s)
    db.commit()
    db.refresh(s)
    return _negotiation_public(s)


@router.post("/negotiation/{session_id}/respond")
def respond_negotiation(session_id: int, data: NegotiationRespondRequest, db: Session = Depends(get_db)):
    s = db.query(NegotiationSession).filter(NegotiationSession.id == session_id).first()
    if not s:
        raise HTTPException(404, "Negotiation not found")
    if s.completed_at:
        raise HTTPException(409, "This simulation is already finished.")
    if not (data.message or "").strip():
        raise HTTPException(400, "Message is empty.")

    rounds = list(s.rounds or [])
    rounds.append({"role": "user", "text": data.message, "ts": datetime.utcnow().isoformat()})
    reply = TutorAI(db).negotiation_reply(s.scenario or {}, rounds, data.message)
    rounds.append({"role": "counterpart", "text": reply, "ts": datetime.utcnow().isoformat()})
    s.rounds = rounds
    db.commit()
    db.refresh(s)
    return _negotiation_public(s)


@router.post("/negotiation/{session_id}/finish")
def finish_negotiation(session_id: int, db: Session = Depends(get_db)):
    s = db.query(NegotiationSession).filter(NegotiationSession.id == session_id).first()
    if not s:
        raise HTTPException(404, "Negotiation not found")
    if s.completed_at:
        return _negotiation_public(s)  # idempotent
    outcome = TutorAI(db).negotiation_analysis(s.scenario or {}, s.rounds or [])
    s.outcome = outcome
    s.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    crud.log_agent_action(db, "tutor", "negotiation_analysis",
                          {"session_id": s.id}, {"score": outcome.get("score")}, "success")
    return _negotiation_public(s)


@router.get("/negotiation/{session_id}")
def get_negotiation(session_id: int, db: Session = Depends(get_db)):
    s = db.query(NegotiationSession).filter(NegotiationSession.id == session_id).first()
    if not s:
        raise HTTPException(404, "Negotiation not found")
    return _negotiation_public(s)


# ══════════════════════════════════════════════════════════════════
# Progress tests (weekly / monthly)
# ══════════════════════════════════════════════════════════════════

def _modules_studied(db: Session, days: int) -> List[LearningModule]:
    """Modules with mastery activity in the window, or assigned in daily
    sessions — falls back to all actionable now-tier modules."""
    since = datetime.utcnow() - timedelta(days=days)
    ids: set = set()
    for e in db.query(MasteryEntry).filter(MasteryEntry.created_at >= since).all():
        ids.add(e.module_id)
    since_str = since.strftime("%Y-%m-%d")
    for sess in db.query(DailySession).filter(DailySession.date >= since_str).all():
        for mid in (sess.modules_assigned or []):
            ids.add(mid)
    if ids:
        mods = db.query(LearningModule).filter(LearningModule.id.in_(ids)).all()
        if mods:
            return mods
    # Fallback: anything the learner could reasonably be tested on.
    return (
        db.query(LearningModule)
        .filter(LearningModule.tier == "now",
                LearningModule.status.in_(["in_progress", "mastered", "available"]))
        .order_by(LearningModule.track_id, LearningModule.order_index)
        .all()
    )


@router.get("/tests/upcoming")
def upcoming_test(db: Session = Depends(get_db)):
    """Report when the next weekly/monthly review is due (most recent test of
    each type vs. its cadence)."""
    def _last(t: str):
        return db.query(ProgressTest).filter(ProgressTest.type == t).order_by(desc(ProgressTest.created_at)).first()

    now = datetime.utcnow()
    out = {}
    for t, cadence in (("weekly", 7), ("monthly", 30)):
        last = _last(t)
        if not last:
            out[t] = {"due": True, "due_in_days": 0, "last_taken": None, "last_score": None}
        else:
            age = (now - last.created_at).days if last.created_at else cadence
            out[t] = {
                "due": age >= cadence,
                "due_in_days": max(0, cadence - age),
                "last_taken": last.created_at.isoformat() if last.created_at else None,
                "last_score": last.score_overall,
            }
    # Soonest actionable test.
    if out["weekly"]["due"]:
        out["next"] = "weekly"
    elif out["monthly"]["due"]:
        out["next"] = "monthly"
    elif out["weekly"]["due_in_days"] <= out["monthly"]["due_in_days"]:
        out["next"] = "weekly"
    else:
        out["next"] = "monthly"
    return out


@router.post("/tests/generate")
def generate_test(data: TestGenerateRequest, db: Session = Depends(get_db)):
    if data.type not in ("weekly", "monthly"):
        raise HTTPException(400, "type must be 'weekly' or 'monthly'")
    days = 30 if data.type == "monthly" else 7
    modules = _modules_studied(db, days)
    if not modules:
        raise HTTPException(409, "No modules studied yet — do a few lessons first.")
    tutor = TutorAI(db)
    questions = tutor.generate_progress_test(data.type, modules)
    if not questions:
        raise HTTPException(502, "Could not generate a test right now. Try again shortly.")
    now = datetime.utcnow()
    t = ProgressTest(
        type=data.type,
        period_start=(now - timedelta(days=days)).strftime("%Y-%m-%d"),
        period_end=now.strftime("%Y-%m-%d"),
        questions=questions,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    crud.log_agent_action(db, "tutor", "generate_progress_test",
                          {"type": data.type, "modules": len(modules)},
                          {"questions": len(questions)}, "success")
    return _test_public(t, reveal=False)


@router.get("/tests/history")
def tests_history(db: Session = Depends(get_db)):
    tests = db.query(ProgressTest).order_by(desc(ProgressTest.created_at)).all()
    return [
        {"id": t.id, "type": t.type, "period_start": t.period_start,
         "period_end": t.period_end, "score_overall": t.score_overall,
         "scores_by_track": t.scores_by_track,
         "submitted_at": t.submitted_at.isoformat() if t.submitted_at else None,
         "created_at": t.created_at.isoformat() if t.created_at else None}
        for t in tests
    ]


@router.get("/tests/{test_id}")
def get_test(test_id: int, db: Session = Depends(get_db)):
    t = db.query(ProgressTest).filter(ProgressTest.id == test_id).first()
    if not t:
        raise HTTPException(404, "Test not found")
    return _test_public(t, reveal=t.submitted_at is not None)


@router.post("/tests/{test_id}/submit")
def submit_test(test_id: int, data: TestSubmitRequest, db: Session = Depends(get_db)):
    t = db.query(ProgressTest).filter(ProgressTest.id == test_id).first()
    if not t:
        raise HTTPException(404, "Test not found")
    if t.submitted_at:
        raise HTTPException(409, "This test has already been submitted.")

    questions = t.questions or []
    total = len(questions)
    correct = 0
    per_track_total: Dict[str, int] = {}
    per_track_correct: Dict[str, int] = {}
    per_question = []
    for i, q in enumerate(questions):
        chosen = data.answers[i] if i < len(data.answers) else None
        right = (chosen is not None and chosen == q.get("correct"))
        if right:
            correct += 1
        tc = q.get("track_code") or "?"
        per_track_total[tc] = per_track_total.get(tc, 0) + 1
        per_track_correct[tc] = per_track_correct.get(tc, 0) + (1 if right else 0)
        per_question.append({
            "question": q.get("question"),
            "chosen_index": chosen,
            "correct_index": q.get("correct"),
            "is_correct": right,
            "explanation": q.get("explanation", ""),
            "track_code": tc,
        })

    overall = round((correct / total) * 100) if total else 0
    by_track = {
        tc: round((per_track_correct[tc] / per_track_total[tc]) * 100)
        for tc in per_track_total
    }
    t.answers = data.answers
    t.submitted_at = datetime.utcnow()
    t.score_overall = overall
    t.scores_by_track = by_track
    db.commit()

    crud.log_agent_action(db, "tutor", "submit_progress_test",
                          {"test_id": t.id}, {"overall": overall}, "success")
    return {
        "id": t.id, "type": t.type, "score_overall": overall,
        "correct": correct, "total": total,
        "scores_by_track": by_track, "per_question": per_question,
    }


# ══════════════════════════════════════════════════════════════════
# Dashboard aggregation
# ══════════════════════════════════════════════════════════════════

dashboard_router = APIRouter(prefix="/api/dashboard", tags=["titan"])


@dashboard_router.get("/titan-track")
def titan_dashboard(db: Session = Depends(get_db)):
    tracks_data = list_tracks(db)
    now_tracks = [t for t in tracks_data if t.get("target_tier") != "horizon"]
    horizon_tracks = [t for t in tracks_data if t.get("target_tier") == "horizon"]

    # Active projects (anything started but not yet graded, newest first).
    active_projects = [
        _project_public(db, p) for p in
        db.query(ModuleProject)
        .filter(ModuleProject.status.in_(["in_progress", "submitted"]))
        .order_by(desc(ModuleProject.updated_at)).limit(6).all()
    ]

    return {
        "streak": _streak_summary(db),
        "now_tracks": now_tracks,
        "horizon_tracks": horizon_tracks,
        "schedule": {"slots": (lambda p: p.slots if p and p.slots else DEFAULT_SLOTS)(
            db.query(LessonSchedulePreference).order_by(desc(LessonSchedulePreference.id)).first())},
        "today_lessons": _today_lessons(db),
        "active_projects": active_projects,
        "upcoming_test": upcoming_test(db),
        "reps_pending_reflection": [
            _serialize(r) for r in
            db.query(LeadershipRep)
            .filter((LeadershipRep.user_reflection.is_(None)) | (LeadershipRep.user_reflection == ""))
            .order_by(desc(LeadershipRep.date)).limit(5).all()
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }
