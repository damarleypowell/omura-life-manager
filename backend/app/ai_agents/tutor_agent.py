"""
Omura Tutor AI Agent — the Titan Track brain.

Follows the same worker-agent pattern as Health AI / Finance AI: a focused
agent the Supervisor can delegate to, not a separate chatbot. Uses the shared
`call_claude` caller (Anthropic primary, Gemini fallback) and always degrades
to a deterministic fallback so endpoints never hard-fail when the AI is down.

Responsibilities (see TITAN_TRACK_SPEC §4):
- Adaptive daily-session assembly across the now-tier tracks
- Visual + quiz + explain-back content generation, grounded in research_basis
- Gatekeeper grading (quiz) and Socratic explain-back checking
- Leadership-rep after-action reviews
- Structural QA (Layer 1) + grounding (Layer 3); a non-blocking LLM judge (Layer 2)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database.models import (
    LearningTrack, LearningModule, MasteryEntry, LeadershipRep,
    StreakLog, DailySession, ModuleQualityCheck,
    Project, Lead, TaskStatus,
)
from backend.app.ai_agents._claude_caller import call_claude_json
from backend.app.utils.logging import OmuraLogger

# Gate threshold — quiz must clear this AND explain-back must pass.
QUIZ_PASS_THRESHOLD = 80

# Lesson-content schema version. Bump when the generated_content shape changes
# so previously-cached lessons (missing new fields) are regenerated on next view
# instead of being served stale. v2 adds: big_picture, historical_example,
# modern_practice, exercises, project_brief.
CONTENT_SCHEMA_VERSION = 2

# The Tutor uses Sonnet (richer lesson generation) rather than the shared
# Haiku default. Falls back to Gemini automatically if Anthropic is unavailable.
TUTOR_MODEL = "claude-sonnet-4-6"

# Confidence note shown in the UI badge (the "what this means" one-liner).
CONFIDENCE_NOTES = {
    "strong": "STRONG: replicated across multiple good-quality studies — safe to build on.",
    "moderate": "MODERATE: a real but smaller or noisier effect — useful, not guaranteed.",
    "contested": "CONTESTED: live disagreement in the research — treat this as a bet worth testing on yourself.",
    "theoretical": "THEORETICAL: model or extrapolation, not directly tested as a training intervention.",
}


def _frozen_content_for(module) -> Optional[Dict[str, Any]]:
    """Return the pre-authored, frozen lesson content for a module's phase_code,
    if a baked course file exists. Safe no-op if the file isn't present yet."""
    if not module or not getattr(module, "phase_code", None):
        return None
    try:
        from backend.app.database.titan_content import TITAN_CONTENT
    except Exception:
        return None
    entry = TITAN_CONTENT.get(module.phase_code)
    return dict(entry) if isinstance(entry, dict) else None


class TutorAI:
    """AI agent for the Titan Track daily learning system."""

    AGENT_NAME = "tutor"

    def __init__(self, db_session: Session) -> None:
        self.db = db_session
        self.logger = OmuraLogger("tutor_ai")

    # ── Public: session assembly ────────────────────────────────────

    def get_daily_session(self, energy_level: Optional[str] = None) -> Dict[str, Any]:
        """Fetch today's session, or assemble a new one if none exists yet.

        The session shape adapts to current load: a heavy business week
        (many active projects / pending follow-ups) or a reported low energy
        level skews the day lighter and more review-oriented.
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        existing = (
            self.db.query(DailySession)
            .filter(DailySession.date == today)
            .order_by(desc(DailySession.created_at))
            .first()
        )
        if existing:
            if energy_level and not existing.energy_level_reported:
                existing.energy_level_reported = energy_level
                self.db.commit()
            return self._serialize_session(existing)

        shape = self._session_shape(energy_level)
        primary = self._select_primary_module()

        payload: Dict[str, Any] = {
            "session_shape": shape,
            "generated_at": datetime.utcnow().isoformat(),
        }
        modules_assigned: List[int] = []

        if primary is not None:
            content = self.generate_module_content(primary.id, light=(shape == "light"))
            payload["primary_module"] = self._module_summary(primary)
            payload["content"] = content
            modules_assigned.append(primary.id)
        else:
            payload["primary_module"] = None
            payload["content"] = None
            payload["message"] = (
                "No active now-tier modules. Seed the roadmap or unlock a track to begin."
            )

        rep = self._select_rep_for_review()
        rep_included = rep is not None
        if rep_included:
            payload["leadership_rep"] = {
                "id": rep.id,
                "source_type": rep.source_type,
                "description": rep.description,
                "ai_after_action_review": rep.ai_after_action_review,
                "presence_score": rep.presence_score,
                "user_reflection": rep.user_reflection,
            }

        session = DailySession(
            date=today,
            modules_assigned=modules_assigned,
            session_payload=payload,
            leadership_rep_review_included=rep_included,
            leadership_rep_id=rep.id if rep else None,
            energy_level_reported=energy_level,
        )
        self.db.add(session)
        try:
            self.db.commit()
            self.db.refresh(session)
        except IntegrityError:
            # Race: a concurrent request already created today's session.
            # The unique constraint on DailySession.date guarantees one/day —
            # roll back and return the row that won.
            self.db.rollback()
            existing = (
                self.db.query(DailySession)
                .filter(DailySession.date == today)
                .order_by(desc(DailySession.created_at))
                .first()
            )
            if existing:
                return self._serialize_session(existing)
            raise
        return self._serialize_session(session)

    # ── Public: module content generation (visual + quiz + explain-back) ──

    def generate_module_content(self, module_id: int, light: bool = False,
                                force: bool = False) -> Dict[str, Any]:
        """Generate (and cache) the visual + quiz + explain-back content for a
        module, grounded in its specific research_basis (QA Layer 3).

        Cached on ``module.extra_data['generated_content']`` so quiz grading
        and explain-back checking score against stable content. Regenerated
        only when missing or ``force`` is set (e.g. two thumbs-down).

        The returned dict carries an internal ``_quiz_key`` with answer
        indices; API serializers strip ``_``-prefixed keys before responding.
        """
        module = self.db.query(LearningModule).filter(LearningModule.id == module_id).first()
        if not module:
            return {"error": f"Module {module_id} not found"}

        cached = (module.extra_data or {}).get("generated_content")
        if cached and not force and cached.get("_schema_version") == CONTENT_SCHEMA_VERSION:
            return cached

        num_questions = 3 if light else 4

        # Prefer pre-authored, frozen course content (baked once into
        # titan_content.py — see scripts/bake_titan_content.py). Lessons are then
        # instant and stable instead of re-generated on every view; the AI is
        # only the fallback for a module that has no authored lesson yet.
        frozen = None if force else _frozen_content_for(module)
        if frozen:
            content = dict(frozen)
            content["_schema_version"] = CONTENT_SCHEMA_VERSION
            content.setdefault("_structural_ok", True)
            content.setdefault("confidence_level", module.confidence_level)
            content.setdefault("confidence_note",
                               module.confidence_note or CONFIDENCE_NOTES.get(module.confidence_level, ""))
        else:
            content = self._ai_generate_content(module, num_questions)
            content = self._structural_validate(content, module, num_questions)

        # Persist a quality-check record (Layer 1 result; Layer 2 judge optional)
        try:
            qc = ModuleQualityCheck(
                module_id=module.id,
                generation_attempt=int((module.extra_data or {}).get("gen_attempts", 0)) + 1,
                judge_scores={"structural": content.get("_structural_ok", True)},
                passed=bool(content.get("_structural_ok", True)),
                rejection_reason=content.get("_structural_reason"),
            )
            self.db.add(qc)
        except Exception as exc:  # logging/QA must never break generation
            self.logger.warning(f"Quality-check log failed: {exc}")

        # Cache on the module
        extra = dict(module.extra_data or {})
        extra["generated_content"] = content
        extra["gen_attempts"] = int(extra.get("gen_attempts", 0)) + 1
        module.extra_data = extra
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
        return content

    # ── Public: gatekeeper grading ──────────────────────────────────

    def grade_module_attempt(self, module_id: int,
                             answers: List[int]) -> Dict[str, Any]:
        """Grade a quiz submission against the module's cached quiz key.

        ``answers`` is a list of chosen option indices, one per question.
        Returns the 0-100 score, per-question correctness, and feedback.
        """
        content = self.generate_module_content(module_id)
        if "error" in content:
            return content

        key = content.get("_quiz_key") or []
        quiz = content.get("quiz") or []
        if not key:
            return {"score": 0, "correct": 0, "total": 0,
                    "passed_quiz": False, "threshold": QUIZ_PASS_THRESHOLD,
                    "feedback": "No quiz available for this module.", "per_question": []}

        total = len(key)
        per_question = []
        correct = 0
        for i, entry in enumerate(key):
            chosen = answers[i] if i < len(answers) else None
            right = (chosen is not None and chosen == entry.get("answer_index"))
            if right:
                correct += 1
            per_question.append({
                "question": quiz[i]["question"] if i < len(quiz) else "",
                "chosen_index": chosen,
                "correct_index": entry.get("answer_index"),
                "is_correct": right,
                "explanation": entry.get("explanation", ""),
            })

        score = round((correct / total) * 100) if total else 0
        passed_quiz = score >= QUIZ_PASS_THRESHOLD
        feedback = (
            f"You scored {score}% ({correct}/{total}). "
            + ("That clears the quiz gate — now prove it in the explain-back."
               if passed_quiz else
               f"You need {QUIZ_PASS_THRESHOLD}% to clear the gate. Review the explanations and retry.")
        )
        return {
            "score": score,
            "correct": correct,
            "total": total,
            "passed_quiz": passed_quiz,
            "threshold": QUIZ_PASS_THRESHOLD,
            "per_question": per_question,
            "feedback": feedback,
        }

    # ── Public: Socratic explain-back check ─────────────────────────

    def run_explain_back_check(self, module_id: int, transcript: str,
                               prior_attempts: int = 0) -> Dict[str, Any]:
        """Feynman gate. Judges whether the learner can explain the concept in
        their own words. For horizon / case-study modules the learner must also
        articulate the luck/survivorship factors, not just the winner's tactics.

        Returns a verdict plus, when not yet passing, a guiding Socratic
        follow-up question rather than the answer (unless they have already had
        2-3 guided attempts).
        """
        module = self.db.query(LearningModule).filter(LearningModule.id == module_id).first()
        if not module:
            return {"error": f"Module {module_id} not found"}

        give_answer = prior_attempts >= 2
        verdict = self._ai_explain_back(module, transcript, give_answer)
        verdict["attempts"] = prior_attempts + 1
        verdict["requires_failure_twin"] = bool(module.requires_failure_twin)
        return verdict

    # ── Public: leadership-rep after-action review ──────────────────

    def generate_leadership_rep_review(self, description: str = "",
                                       source_type: str = "manual",
                                       rep_id: Optional[int] = None) -> Dict[str, Any]:
        """Produce an after-action review for a leadership rep, focused on
        clarity under pressure, whether the ask/price was named directly, where
        the conversation got handed away, and silence tolerance."""
        if rep_id is not None:
            rep = self.db.query(LeadershipRep).filter(LeadershipRep.id == rep_id).first()
            if rep:
                description = description or rep.description or ""
                source_type = rep.source_type or source_type

        review = self._ai_rep_review(description, source_type)

        if rep_id is not None and rep:
            rep.ai_after_action_review = review.get("after_action_review")
            rep.presence_score = review.get("presence_score")
            if not rep.avoided_moments:
                rep.avoided_moments = review.get("avoided_moments")
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
        return review

    # ── Public: non-blocking LLM-as-judge (QA Layer 2) ──────────────

    def quality_judge(self, module_id: int) -> Dict[str, Any]:
        """Second-pass rubric grade of a module's generated content. Built per
        §8.3 to be available but NOT block the pipeline — it logs scores so the
        rubric can be tuned once there is real usage data."""
        module = self.db.query(LearningModule).filter(LearningModule.id == module_id).first()
        if not module:
            return {"error": f"Module {module_id} not found"}
        content = (module.extra_data or {}).get("generated_content")
        if not content:
            return {"error": "No generated content to judge yet."}
        return self._ai_judge(module, content)

    # ── Internal: module/track selection ────────────────────────────

    def _select_primary_module(self) -> Optional[LearningModule]:
        """Pick the day's focus module across now-tier tracks. Prefers an
        in-progress module; otherwise rotates across tracks by day so no single
        track dominates, and respects prerequisite gating (only available ones)."""
        in_progress = (
            self.db.query(LearningModule)
            .filter(LearningModule.tier == "now", LearningModule.status == "in_progress")
            .order_by(LearningModule.order_index)
            .first()
        )
        if in_progress:
            return in_progress

        available = (
            self.db.query(LearningModule)
            .join(LearningTrack, LearningModule.track_id == LearningTrack.id)
            .filter(LearningModule.tier == "now", LearningModule.status == "available")
            .order_by(LearningTrack.order_index, LearningModule.order_index)
            .all()
        )
        if not available:
            return None

        # Rotate across the distinct tracks that have something available.
        track_ids = []
        for m in available:
            if m.track_id not in track_ids:
                track_ids.append(m.track_id)
        day_index = datetime.utcnow().timetuple().tm_yday % len(track_ids)
        chosen_track = track_ids[day_index]
        for m in available:
            if m.track_id == chosen_track:
                return m
        return available[0]

    def _select_rep_for_review(self) -> Optional[LeadershipRep]:
        """Surface a leadership rep for reflection: the most recent one that
        has an AI review but no user reflection yet."""
        return (
            self.db.query(LeadershipRep)
            .filter(LeadershipRep.ai_after_action_review.isnot(None))
            .filter((LeadershipRep.user_reflection.is_(None)) | (LeadershipRep.user_reflection == ""))
            .order_by(desc(LeadershipRep.date))
            .first()
        )

    def _session_shape(self, energy_level: Optional[str]) -> str:
        """'light' (review-leaning) vs 'standard', from energy + business load."""
        if energy_level == "low":
            return "light"
        try:
            active_projects = self.db.query(Project).filter(
                Project.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
            ).count()
            pending_leads = self.db.query(Lead).filter(
                Lead.next_followup <= datetime.utcnow()
            ).count()
            load = active_projects + pending_leads
        except Exception:
            load = 0
        return "light" if load >= 8 else "standard"

    # ── Internal: serialization helpers ─────────────────────────────

    @staticmethod
    def _module_summary(m: LearningModule) -> Dict[str, Any]:
        return {
            "id": m.id,
            "track_id": m.track_id,
            "title": m.title,
            "description": m.description,
            "tier": m.tier,
            "format": m.format,
            "confidence_level": m.confidence_level,
            "confidence_note": m.confidence_note or CONFIDENCE_NOTES.get(m.confidence_level, ""),
            "research_basis": m.research_basis,
            "phase_code": m.phase_code,
            "week_number": m.week_number,
            "culminating_artifact": m.culminating_artifact,
            "requires_failure_twin": bool(m.requires_failure_twin),
            "status": m.status,
        }

    @staticmethod
    def _public_content(content: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Strip internal (``_``-prefixed) keys — e.g. the quiz answer key."""
        if not isinstance(content, dict):
            return content
        return {k: v for k, v in content.items() if not k.startswith("_")}

    def _serialize_session(self, session: DailySession) -> Dict[str, Any]:
        payload = dict(session.session_payload or {})
        if "content" in payload:
            payload["content"] = self._public_content(payload.get("content"))
        return {
            "id": session.id,
            "date": session.date,
            "modules_assigned": session.modules_assigned or [],
            "leadership_rep_review_included": session.leadership_rep_review_included,
            "leadership_rep_id": session.leadership_rep_id,
            "actual_minutes_spent": session.actual_minutes_spent,
            "energy_level_reported": session.energy_level_reported,
            "started": session.started,
            "completed": session.completed,
            "payload": payload,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        }

    # ── Internal: structural QA (Layer 1) ───────────────────────────

    def _structural_validate(self, content: Dict[str, Any], module: LearningModule,
                             num_questions: int) -> Dict[str, Any]:
        """Reject/repair generated content missing required components. A
        genuinely lazy generation skips or genericizes one of these fields."""
        reasons: List[str] = []
        content = dict(content or {})

        if not (content.get("concept") or "").strip():
            reasons.append("missing concept explanation")
            content["concept"] = self._fallback_concept(module)

        if not (content.get("big_picture") or "").strip():
            content["big_picture"] = (
                f"{module.title} is a building block toward founder-grade judgment. "
                "Learn it well and it compounds."
            )

        he = content.get("historical_example")
        if not isinstance(he, dict) or not (he.get("story") or "").strip():
            content["historical_example"] = self._fallback_historical(module)

        if not (content.get("modern_practice") or "").strip():
            content["modern_practice"] = (
                "Today, applying this means turning the principle into one concrete move in your "
                "agency or finance work this week — small, real, and observable."
            )

        ex = content.get("exercises")
        if not isinstance(ex, list) or not ex:
            content["exercises"] = self._fallback_exercises(module)
        else:
            content["exercises"] = [
                {"task": str(e.get("task", "")).strip() or "Apply the idea to a real situation.",
                 "minutes": int(e.get("minutes", 10)) if isinstance(e, dict) and str(e.get("minutes", "")).isdigit() else 10}
                for e in ex if isinstance(e, dict)
            ] or self._fallback_exercises(module)

        pb = content.get("project_brief")
        if not isinstance(pb, dict) or not (pb.get("title") or "").strip() or not isinstance(pb.get("steps"), list) or not pb.get("steps"):
            content["project_brief"] = self._fallback_project(module)
        else:
            # Ensure required project fields exist.
            pb.setdefault("description", module.description or "Build something that proves the skill.")
            pb.setdefault("starter_code", None)
            pb.setdefault("estimated_hours", 3)
            pb.setdefault("submission_format", "writing")
            if not isinstance(pb.get("rubric"), list) or not pb["rubric"]:
                pb["rubric"] = [
                    {"criterion": "Completeness", "max_points": 40},
                    {"criterion": "Correctness / soundness", "max_points": 35},
                    {"criterion": "Clarity of explanation", "max_points": 25},
                ]
            content["project_brief"] = pb

        diagram = content.get("diagram")
        if not isinstance(diagram, dict) or not (diagram.get("nodes") or diagram.get("columns")):
            reasons.append("missing or empty diagram")
            content["diagram"] = self._fallback_diagram(module)

        quiz = content.get("quiz")
        if not isinstance(quiz, list) or len(quiz) < 3:
            reasons.append("fewer than 3 quiz questions")
            quiz, key = self._fallback_quiz(module, num_questions)
            content["quiz"] = quiz
            content["_quiz_key"] = key
        else:
            # Ensure each question is well-formed and an answer key exists.
            if not content.get("_quiz_key") or len(content["_quiz_key"]) != len(quiz):
                reasons.append("quiz answer key malformed")
                quiz, key = self._fallback_quiz(module, num_questions)
                content["quiz"] = quiz
                content["_quiz_key"] = key

        if not (content.get("explain_back_prompt") or "").strip():
            reasons.append("missing explain-back prompt")
            content["explain_back_prompt"] = self._fallback_explain_prompt(module)

        if not (content.get("citation") or "").strip():
            content["citation"] = module.research_basis or "See module research basis."

        content["confidence_level"] = module.confidence_level
        content["confidence_note"] = module.confidence_note or CONFIDENCE_NOTES.get(
            module.confidence_level, "")
        content["_schema_version"] = CONTENT_SCHEMA_VERSION
        content["_structural_ok"] = len(reasons) == 0
        content["_structural_reason"] = "; ".join(reasons) if reasons else None
        return content

    # ── Internal: AI calls (each with deterministic fallback) ───────

    def _ai_generate_content(self, module: LearningModule, num_questions: int) -> Dict[str, Any]:
        system = (
            "You are the Tutor AI for Omura's Titan Track — a world-class teacher who makes hard "
            "ideas easy. You teach the way Robert Greene does: state the concept in plain language, "
            "then bring it to life with ONE specific historical figure and moment, then show what it "
            "looks like in the learner's world today. Take inspiration from the best courses on earth "
            "(fast.ai's learn-by-building, 3Blue1Brown's intuition-before-symbols, Harvard Business "
            "School cases, Masterclass storytelling). You generate ONE module's full lesson + a real "
            "hands-on project. Ground everything in the module's specific research_basis; never drift "
            "to generic claims the citation does not support. If confidence is CONTESTED or "
            "THEORETICAL, communicate that uncertainty honestly. Tie examples to the learner's real "
            "context (IronLogic AI agency, Gotham Financial, boxing) only where it maps naturally. "
            "Use plain, concrete language a smart 16-year-old could follow. Respond with valid JSON only."
        )
        ff = ""
        if module.requires_failure_twin:
            ff = (
                " This is a 'study the greats' / case-study module: the content, quiz, and the "
                "historical example MUST cover a failure twin (someone who did the same and failed) "
                "and the luck/timing factors, not just the winner's tactics."
            )
        prompt = (
            f"Module: {module.title}\n"
            f"Description: {module.description or ''}\n"
            f"Research basis (cite this specifically): {module.research_basis or 'n/a'}\n"
            f"Confidence: {module.confidence_level.upper()} — {module.confidence_note or ''}\n"
            f"Format: {module.format}.{ff}\n\n"
            f"Produce JSON with EXACTLY these keys:\n"
            '{\n'
            '  "big_picture": "1 short paragraph (<= 55 words): what this is and why it matters to an ambitious founder — the hook",\n'
            '  "concept": "2-3 SHORT paragraphs (<= 110 words total), separated by a blank line, plain language grounded in the citation",\n'
            '  "historical_example": {"figure": "one specific real, well-known person (so a portrait exists)", "era": "<= 6 words",\n'
            '     "story": "a concrete 50-85 word story of what they actually did", "key_lesson": "<= 22 words pulling out the principle"},\n'
            '  "modern_practice": "1 paragraph (<= 70 words): exactly what applying this looks like for the learner TODAY (agency/finance/leadership)",\n'
            '  "diagram": {"type": "flow|comparison|cycle", "title": "<= 8 words",\n'
            '     "nodes": ["step 1","step 2",...]   // 3-5 short items, for flow/cycle\n'
            '     OR "columns": [{"label":"A","points":["..."]},{"label":"B","points":["..."]}] // for comparison },\n'
            '  "exercises": [{"task": "concrete thing to do right now (<= 22 words)", "minutes": 10}],  // 2-3 items\n'
            f'  "quiz": [{{"question": "<= 25 words", "options": ["a","b","c","d"], "objective": "<= 12 words"}}]  // exactly {num_questions} items,\n'
            '  "answer_key": [{"answer_index": 0, "explanation": "<= 25 words"}],  // one per quiz item, same order\n'
            '  "explain_back_prompt": "one specific prompt (<= 30 words) asking the learner to explain THIS concept",\n'
            '  "project_brief": {\n'
            '     "title": "name of a real thing to build/do (<= 10 words)",\n'
            '     "description": "2-4 sentences on what they will produce and why it cements the skill",\n'
            '     "steps": [{"title": "<= 8 words", "detail": "<= 30 words", "minutes": 30}],  // 3-5 steps\n'
            '     "starter_code": "a short code scaffold if this is a coding project, else null",\n'
            '     "rubric": [{"criterion": "<= 8 words", "max_points": 25}],  // 3-4 criteria summing to ~100\n'
            '     "estimated_hours": 3,\n'
            '     "submission_format": "code|writing|log|recording|negotiation_sim"\n'
            '  },\n'
            '  "citation": "the specific source(s) this rests on"\n'
            '}\n'
            "RULES: Write tight — short, concrete sentences, no filler or throat-clearing; respect every word cap above. "
            "The historical example must be a real, famous, nameable person (one with a known portrait) doing a specific thing — not a vague archetype. "
            "Quiz questions must test the learning objective, not trivia; each needs 3-4 plausible options (<= 15 words each). "
            "The project must produce a REAL artifact (working code, a written analysis, a tracked log, a recording, or a simulation), "
            "sized to its estimated_hours. For Track C presence/negotiation modules prefer submission_format 'negotiation_sim' or 'recording'. "
            "Output ONLY the JSON object — no preamble, no markdown fence, no commentary. Keep it compact so it is complete and valid."
        )
        result = call_claude_json(prompt, system, agent_name="tutor_ai",
                                  temperature=0.45, max_tokens=6500, model=TUTOR_MODEL)
        if not isinstance(result, dict):
            return {}

        # Normalize the answer_key into the internal _quiz_key.
        def _safe_idx(v):
            try:
                return int(v)
            except (TypeError, ValueError):
                return 0  # model returned a non-numeric index — never crash the lesson

        key = result.pop("answer_key", None)
        if isinstance(key, list):
            result["_quiz_key"] = [
                {"answer_index": _safe_idx(k.get("answer_index", 0)) if isinstance(k, dict) else 0,
                 "explanation": (k.get("explanation", "") if isinstance(k, dict) else "")}
                for k in key
            ]
        return result

    def _ai_explain_back(self, module: LearningModule, transcript: str,
                         give_answer: bool) -> Dict[str, Any]:
        system = (
            "You are the Tutor AI running a Socratic Feynman-gate check. The learner is trying to "
            "explain a concept in their own words. Judge whether their explanation demonstrates real "
            "understanding (not recitation). Be a fair but demanding examiner. "
            "If they have NOT yet demonstrated it, do NOT give the answer — instead ask ONE guiding "
            "question that exposes the gap. Respond with valid JSON only."
        )
        extra = ""
        if module.requires_failure_twin:
            extra = (
                " To PASS this module the learner MUST articulate the failure twin and the luck/"
                "survivorship/timing factors unprompted — reciting only the winner's tactics fails."
            )
        prompt = (
            f"Module: {module.title}\n"
            f"Research basis: {module.research_basis or 'n/a'}\n"
            f"Concept it covers: {module.description or ''}.{extra}\n\n"
            f"Learner's explanation:\n\"\"\"{transcript}\"\"\"\n\n"
            f"{'You may now give a concise correct explanation since they have had multiple attempts. ' if give_answer else ''}"
            "Respond with JSON: {\n"
            '  "passed": true/false,\n'
            '  "score": 0-100,\n'
            '  "feedback": "1-3 sentences, direct",\n'
            '  "follow_up_question": "a single Socratic question if not passed, else empty",\n'
            '  "model_answer": "concise correct explanation, ONLY if you were told you may give it, else empty"\n'
            "}"
        )
        result = call_claude_json(prompt, system, agent_name="tutor_ai",
                                  temperature=0.3, max_tokens=900, model=TUTOR_MODEL)
        if isinstance(result, dict) and "passed" in result:
            result["passed"] = bool(result.get("passed"))
            try:
                result["score"] = int(result.get("score", 0))
            except (TypeError, ValueError):
                result["score"] = 0
            return result

        # Fallback heuristic: length + keyword overlap with the research basis.
        words = len((transcript or "").split())
        passed = words >= 40
        return {
            "passed": passed,
            "score": min(100, words * 2),
            "feedback": ("Solid length and structure — logged as a pass."
                         if passed else
                         "Too thin to confirm understanding. Explain the mechanism, not just the label."),
            "follow_up_question": "" if passed else "Can you explain WHY this holds, in your own words?",
            "model_answer": "",
        }

    def _ai_rep_review(self, description: str, source_type: str) -> Dict[str, Any]:
        system = (
            "You are the Tutor AI generating an after-action review of a real leadership rep "
            "(a call, pitch, or negotiation). Focus strictly on: clarity under pressure, whether the "
            "ask/price was named directly, where the conversation got handed away, and silence "
            "tolerance. Be specific and direct, not flattering. Respond with valid JSON only."
        )
        prompt = (
            f"Rep type: {source_type}\n"
            f"What happened:\n\"\"\"{description or 'No description provided.'}\"\"\"\n\n"
            "Respond with JSON: {\n"
            '  "after_action_review": "3-5 sentences of specific feedback",\n'
            '  "presence_score": 0-100,\n'
            '  "avoided_moments": "one line naming where they likely shrank or handed control away"\n'
            "}"
        )
        result = call_claude_json(prompt, system, agent_name="tutor_ai",
                                  temperature=0.4, max_tokens=700, model=TUTOR_MODEL)
        if isinstance(result, dict) and result.get("after_action_review"):
            try:
                result["presence_score"] = float(result.get("presence_score", 50))
            except (TypeError, ValueError):
                result["presence_score"] = 50.0
            return result
        return {
            "after_action_review": (
                "Logged. Add a fuller description of the rep (what you asked for, where it stalled) "
                "to get a sharper after-action review."
            ),
            "presence_score": 50.0,
            "avoided_moments": "Note the moment you hesitated to name the price or the next step.",
        }

    def _ai_judge(self, module: LearningModule, content: Dict[str, Any]) -> Dict[str, Any]:
        system = (
            "You are an LLM-as-judge for educational content. Grade the supplied lesson against the "
            "rubric. Do NOT reward length — longer is not better. Respond with valid JSON only."
        )
        prompt = (
            f"Module: {module.title}\nResearch basis: {module.research_basis}\n"
            f"Confidence: {module.confidence_level}\n\n"
            f"Lesson JSON:\n{self._public_content(content)}\n\n"
            "Score 0-100 on each rubric dimension and overall: {\n"
            '  "research_accuracy": 0-100, "pedagogical_soundness": 0-100, "specificity": 0-100,\n'
            '  "assessment_validity": 0-100, "confidence_honesty": 0-100, "calibrated_depth": 0-100,\n'
            '  "overall": 0-100, "notes": "1-2 lines"\n}'
        )
        result = call_claude_json(prompt, system, agent_name="tutor_ai",
                                  temperature=0.2, max_tokens=700, model=TUTOR_MODEL)
        return result if isinstance(result, dict) else {"overall": None, "notes": "judge unavailable"}

    # ── Internal: deterministic fallbacks (AI-down resilience) ──────

    @staticmethod
    def _fallback_concept(module: LearningModule) -> str:
        return (
            f"{module.title}. {module.description or ''}\n\n"
            f"This module rests on: {module.research_basis or 'the cited research'}. "
            f"Confidence level: {module.confidence_level.upper()}. "
            f"{CONFIDENCE_NOTES.get(module.confidence_level, '')}"
        )

    @staticmethod
    def _fallback_diagram(module: LearningModule) -> Dict[str, Any]:
        return {
            "type": "flow",
            "title": module.title,
            "nodes": ["Learn the concept", "See the evidence", "Apply to a real case", "Prove it (explain-back)"],
        }

    @staticmethod
    def _fallback_quiz(module: LearningModule, num_questions: int):
        base = [
            {
                "question": f"What is the core claim of: {module.title}?",
                "options": [
                    (module.description or "The module's main idea")[:120],
                    "That practice alone guarantees elite results",
                    "That the effect is fully settled and universal",
                    "That none of it has any supporting evidence",
                ],
                "objective": "Identify the central, evidence-grounded claim.",
            },
            {
                "question": f"What confidence level does this module carry?",
                "options": ["strong", "moderate", "contested", "theoretical"],
                "objective": "Recognize how much certainty to assign.",
            },
            {
                "question": "How should a CONTESTED or THEORETICAL finding be treated?",
                "options": [
                    "As a bet worth testing on yourself, not a settled prescription",
                    "As proven fact to follow blindly",
                    "As something to ignore entirely",
                    "As identical to a STRONG finding",
                ],
                "objective": "Apply calibrated trust to evidence.",
            },
            {
                "question": "What is the right next step after the quiz?",
                "options": [
                    "Explain the concept back in your own words to prove understanding",
                    "Self-report 'I get it' and move on",
                    "Re-read the text passively",
                    "Skip to the next module",
                ],
                "objective": "Reinforce the mastery gate.",
            },
        ]
        levels = ["strong", "moderate", "contested", "theoretical"]
        correct_conf = levels.index(module.confidence_level) if module.confidence_level in levels else 1
        quiz = base[:max(3, min(num_questions, 4))]
        key = [
            {"answer_index": 0, "explanation": "The description states the central claim."},
            {"answer_index": correct_conf, "explanation": f"This module is tagged {module.confidence_level.upper()}."},
            {"answer_index": 0, "explanation": "Contested/theoretical findings are bets to test, not settled law."},
            {"answer_index": 0, "explanation": "Explain-back is the gate; self-report never counts."},
        ][:len(quiz)]
        return quiz, key

    @staticmethod
    def _fallback_explain_prompt(module: LearningModule) -> str:
        if module.requires_failure_twin:
            return (
                f"Explain {module.title} in your own words — and name a failure twin "
                "plus the luck/timing factors, not just what the winner did."
            )
        return (
            f"In your own words, explain the core mechanism behind '{module.title}' "
            "and why it holds — not just what it is."
        )

    @staticmethod
    def _fallback_historical(module: LearningModule) -> Dict[str, Any]:
        return {
            "figure": "A documented practitioner",
            "era": "history",
            "story": (
                f"Across history, people who mastered '{module.title}' did so deliberately — "
                "repeating the same core move under real stakes until it became second nature. "
                "The research behind this module captures that same pattern."
            ),
            "key_lesson": "The principle shows up wherever someone practiced it under real pressure, not in theory.",
        }

    @staticmethod
    def _fallback_exercises(module: LearningModule) -> List[Dict[str, Any]]:
        return [
            {"task": f"Write, in 3 sentences, the core claim of '{module.title}' in your own words.", "minutes": 10},
            {"task": "Find one real situation from your week where this applies and note how.", "minutes": 15},
            {"task": "Decide one concrete change you will make based on it.", "minutes": 10},
        ]

    @staticmethod
    def _fallback_project(module: LearningModule) -> Dict[str, Any]:
        return {
            "title": f"Apply '{module.title}' to a real case",
            "description": (
                f"Produce a short written analysis that takes the idea behind '{module.title}' "
                "and applies it to a real decision or build in your own work. Make it concrete enough "
                "that someone else could follow your reasoning."
            ),
            "steps": [
                {"title": "Pick a real case", "detail": "Choose an actual decision/build from your work.", "minutes": 15},
                {"title": "Apply the principle", "detail": "Walk through how this module's idea reshapes it.", "minutes": 40},
                {"title": "Write the takeaway", "detail": "One paragraph: what you'd do differently and why.", "minutes": 20},
            ],
            "starter_code": None,
            "rubric": [
                {"criterion": "Used a real, specific case", "max_points": 30},
                {"criterion": "Correctly applied the principle", "max_points": 45},
                {"criterion": "Clear, honest reasoning", "max_points": 25},
            ],
            "estimated_hours": 2,
            "submission_format": "writing",
        }

    # ── Public: project grading ─────────────────────────────────────

    def grade_project_submission(self, module: LearningModule, submission_text: str,
                                 rubric: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Grade a hands-on project submission against its rubric. Returns a
        0-100 score, pass flag, strengths, improvements, and a short summary.
        Always degrades to a deterministic encouraging-but-honest fallback."""
        rubric = rubric or [
            {"criterion": "Completeness", "max_points": 40},
            {"criterion": "Correctness / soundness", "max_points": 35},
            {"criterion": "Clarity", "max_points": 25},
        ]
        system = (
            "You are the Tutor AI grading a learner's hands-on project. Be a fair, demanding, "
            "specific mentor — never flattering, never cruel. Reward real work and correct "
            "reasoning; dock vagueness, hand-waving, and skipped steps. Respond with valid JSON only."
        )
        rubric_str = "; ".join(f"{r.get('criterion')} (max {r.get('max_points')})" for r in rubric)
        prompt = (
            f"Module: {module.title}\n"
            f"What the module teaches: {module.description or ''}\n"
            f"Research basis: {module.research_basis or 'n/a'}\n"
            f"Rubric: {rubric_str}\n\n"
            f"Learner's submission:\n\"\"\"{(submission_text or '').strip()[:6000]}\"\"\"\n\n"
            "Score each rubric criterion, sum to an overall 0-100, and respond with JSON: {\n"
            '  "score": 0-100,\n'
            '  "passed": true/false,   // true if score >= 80 AND no criterion is near-zero\n'
            '  "per_rubric": [{"criterion": "...", "points": 0, "max_points": 0, "note": "<= 20 words"}],\n'
            '  "strengths": ["<= 15 words", ...],   // 1-3\n'
            '  "improvements": ["<= 15 words", ...], // 1-3, specific next steps\n'
            '  "summary": "2-3 sentences, direct"\n'
            "}"
        )
        result = call_claude_json(prompt, system, agent_name="tutor_ai",
                                  temperature=0.3, max_tokens=1200, model=TUTOR_MODEL)
        if isinstance(result, dict) and "score" in result:
            try:
                result["score"] = max(0, min(100, int(round(float(result.get("score", 0))))))
            except (TypeError, ValueError):
                result["score"] = 0
            result["passed"] = bool(result.get("passed")) and result["score"] >= 80
            return result

        # Fallback: reward genuine effort by length/structure, stay honest.
        words = len((submission_text or "").split())
        score = max(0, min(95, 40 + words // 8))
        passed = words >= 120
        return {
            "score": score,
            "passed": passed,
            "per_rubric": [{"criterion": r.get("criterion"), "points": None,
                            "max_points": r.get("max_points"), "note": "AI grader offline — logged for review."} for r in rubric],
            "strengths": ["You shipped a real attempt — that's the hard part."] if passed
                         else ["You started — now go deeper."],
            "improvements": ["Add more detail and show your reasoning step by step.",
                             "Tie it explicitly back to the module's core principle."],
            "summary": ("Logged. The AI grader is offline, so this is a provisional pass based on "
                        "substance and effort — revisit when it's back for a sharper grade."
                        if passed else
                        "Too thin to confirm. Expand it with a concrete worked example and resubmit."),
        }

    # ── Public: negotiation / leadership simulation ─────────────────

    def negotiation_scenario(self, module: Optional[LearningModule] = None,
                             scenario_type: Optional[str] = None) -> Dict[str, Any]:
        """Generate a negotiation scenario + the counterpart's opening line."""
        system = (
            "You are the Tutor AI setting up a realistic negotiation/leadership simulation for an "
            "ambitious founder. Pick stakes that feel real (a client deal, a raise, a vendor, a "
            "co-founder split). You will later PLAY the counterpart. Respond with valid JSON only."
        )
        ctx = f"Tie it to: {module.title}. {module.description or ''}\n" if module else ""
        if scenario_type:
            ctx += f"Scenario type requested: {scenario_type}\n"
        prompt = (
            f"{ctx}\nProduce JSON: {{\n"
            '  "role": "who the LEARNER is (<= 12 words)",\n'
            '  "counterpart": "who YOU (the AI) play (<= 12 words)",\n'
            '  "objective": "the learner\'s goal (<= 20 words)",\n'
            '  "stakes": "what is on the line, visible to BOTH sides (<= 30 words)",\n'
            '  "_counterpart_position": "the counterpart\'s HIDDEN goal / BATNA / walk-away point — '
            'PRIVATE, the learner must never see this (<= 30 words)",\n'
            '  "opening": "the counterpart\'s first line to open the negotiation (in character, <= 40 words)"\n'
            "}"
        )
        result = call_claude_json(prompt, system, agent_name="tutor_ai",
                                  temperature=0.6, max_tokens=700, model=TUTOR_MODEL)
        if isinstance(result, dict) and result.get("opening"):
            return result
        return {
            "role": "A founder closing a deal",
            "counterpart": "A cost-conscious prospective client",
            "objective": "Close at a fair price without over-discounting.",
            "stakes": "A 6-month retainer is on the table for both sides.",
            "_counterpart_position": "Likes you, but has two cheaper quotes and will push hard for ~20% off before signing.",
            "opening": "Look, we're interested — but your price is higher than the other quotes we got. Talk me into it.",
        }

    def negotiation_reply(self, scenario: Dict[str, Any], rounds: List[Dict[str, Any]],
                          user_message: str) -> str:
        """Produce the counterpart's next in-character line given the transcript."""
        system = (
            "You are role-playing the COUNTERPART in a negotiation training sim. Stay fully in "
            "character. Be realistic: push back, probe weakness, reward clarity and a firmly named "
            "ask, exploit hedging or over-apologizing. Keep replies to 1-3 sentences. Do NOT break "
            "character or give coaching — that comes later. Output ONLY the counterpart's spoken line."
        )
        transcript = "\n".join(
            f"{'Learner' if r.get('role') == 'user' else 'You'}: {r.get('text','')}" for r in (rounds or [])
        )
        prompt = (
            f"Scenario: You are {scenario.get('counterpart','the counterpart')}. "
            f"{scenario.get('stakes','')}\n"
            f"Your private position (never reveal this outright): "
            f"{scenario.get('_counterpart_position','You want the best deal you can get.')}\n\n"
            f"Transcript so far:\n{transcript}\n\n"
            f"Learner just said: \"{user_message}\"\n\n"
            "Reply with your next line (1-3 sentences), in character."
        )
        from backend.app.ai_agents._claude_caller import call_claude
        line = call_claude(prompt, system, agent_name="tutor_ai",
                           temperature=0.7, max_tokens=300, model=TUTOR_MODEL)
        if line and line.strip():
            return line.strip().strip('"')
        return "Hm. I hear you — but I'm not there yet. Make the case more concrete."

    def negotiation_analysis(self, scenario: Dict[str, Any],
                             rounds: List[Dict[str, Any]]) -> Dict[str, Any]:
        """After-action analysis of a finished negotiation sim."""
        system = (
            "You are the Tutor AI debriefing a finished negotiation sim. Focus on: did they name the "
            "ask/price directly, did they hold the line, where did they give ground for free, did they "
            "tolerate silence, did they trade concessions for value. Be specific and direct. "
            "Respond with valid JSON only."
        )
        transcript = "\n".join(
            f"{'Learner' if r.get('role') == 'user' else 'Counterpart'}: {r.get('text','')}" for r in (rounds or [])
        )
        prompt = (
            f"Scenario: {scenario.get('objective','')}. {scenario.get('stakes','')}\n"
            f"(For your analysis only — the counterpart's hidden position was: "
            f"{scenario.get('_counterpart_position','—')})\n\n"
            f"Full transcript:\n{transcript}\n\n"
            "Respond with JSON: {\n"
            '  "score": 0-100,\n'
            '  "analysis": "3-5 sentences of specific debrief",\n'
            '  "what_worked": ["<= 15 words", ...],   // 1-3\n'
            '  "what_cost_you": ["<= 15 words", ...]  // 1-3 — where they gave ground or shrank\n'
            "}"
        )
        result = call_claude_json(prompt, system, agent_name="tutor_ai",
                                  temperature=0.4, max_tokens=900, model=TUTOR_MODEL)
        if isinstance(result, dict) and result.get("analysis"):
            try:
                result["score"] = max(0, min(100, int(round(float(result.get("score", 50))))))
            except (TypeError, ValueError):
                result["score"] = 50
            return result
        return {
            "score": 50,
            "analysis": ("Logged. The AI debrief is offline — but review the transcript yourself: "
                         "did you name your ask plainly, and where did you discount without getting "
                         "anything back?"),
            "what_worked": ["You completed the rep."],
            "what_cost_you": ["Watch for moments you softened the ask."],
        }

    # ── Public: weekly / monthly progress test ──────────────────────

    def generate_progress_test(self, test_type: str,
                               modules: List[LearningModule]) -> List[Dict[str, Any]]:
        """Build a multi-module review test. ``test_type`` is 'weekly' (~10 Qs)
        or 'monthly' (~20 Qs). Each returned question carries its correct index,
        explanation, module_id and track_code so the API can grade by track.
        Always degrades to a deterministic fallback."""
        target = 20 if test_type == "monthly" else 10
        if not modules:
            return []
        # Map module -> track code for tagging.
        track_codes: Dict[int, str] = {}
        for m in modules:
            tr = self.db.query(LearningTrack).filter(LearningTrack.id == m.track_id).first()
            track_codes[m.id] = tr.code if tr else "?"

        mod_lines = "\n".join(
            f"- id={m.id} track={track_codes.get(m.id,'?')} :: {m.title} — {m.research_basis or ''}"
            for m in modules
        )
        system = (
            "You are the Tutor AI writing a fair, rigorous review test across multiple modules the "
            "learner has studied. Test understanding and application, not trivia. Spread questions "
            "across the modules listed. Respond with valid JSON only."
        )
        prompt = (
            f"Modules studied this period:\n{mod_lines}\n\n"
            f"Write EXACTLY {target} multiple-choice questions spread across these modules. "
            "Respond with JSON: {\n"
            '  "questions": [\n'
            '    {"question": "<= 28 words", "options": ["a","b","c","d"], "correct": 0,\n'
            '     "explanation": "<= 25 words", "module_id": 0, "track_code": "A"}\n'
            "  ]\n}\n"
            "Each question MUST set module_id to one of the ids above and track_code to its track. "
            "Output ONLY the JSON object."
        )
        result = call_claude_json(prompt, system, agent_name="tutor_ai",
                                  temperature=0.4, max_tokens=4096, model=TUTOR_MODEL)
        questions: List[Dict[str, Any]] = []
        if isinstance(result, dict) and isinstance(result.get("questions"), list):
            valid_ids = {m.id for m in modules}
            for q in result["questions"]:
                if not isinstance(q, dict) or not q.get("question") or not isinstance(q.get("options"), list):
                    continue
                mid = q.get("module_id")
                if mid not in valid_ids:
                    mid = modules[0].id
                questions.append({
                    "question": str(q["question"]),
                    "options": [str(o) for o in q["options"]][:4],
                    "correct": int(q.get("correct", 0)) if str(q.get("correct", 0)).isdigit() else 0,
                    "explanation": str(q.get("explanation", "")),
                    "module_id": mid,
                    "track_code": track_codes.get(mid, q.get("track_code", "?")),
                })
        if questions:
            return questions[:target]

        # Fallback: one question per module from its description.
        for m in modules[:target]:
            questions.append({
                "question": f"What is the central, evidence-grounded claim of '{m.title}'?",
                "options": [
                    (m.description or "Its main idea")[:110],
                    "That practice alone guarantees elite results",
                    "That the effect is fully settled and universal",
                    "That none of it has supporting evidence",
                ],
                "correct": 0,
                "explanation": "The description states the central claim.",
                "module_id": m.id,
                "track_code": track_codes.get(m.id, "?"),
            })
        return questions
