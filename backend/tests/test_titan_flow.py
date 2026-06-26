"""
Titan Track QA harness — runnable end-to-end integration test.

Run:  python -m backend.tests.test_titan_flow

Guarantees ZERO calls to any external AI provider: it monkeypatches the
Tutor's ``call_claude_json`` to return None, so every code path exercises the
deterministic fallback. Uses a throwaway SQLite DB. Prints a PASS/FAIL report
and exits non-zero on any failure (so a reviewer can gate on it).
"""

from __future__ import annotations

import os
import sys
import tempfile
import traceback

# ── Isolate from the real environment BEFORE importing app code ──
_TMP_DB = os.path.join(tempfile.gettempdir(), "titan_qa_test.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["REDIS_URL"] = "redis://127.0.0.1:6399/0"  # unreachable -> graceful None

from fastapi import FastAPI                                  # noqa: E402
from fastapi.testclient import TestClient                    # noqa: E402

from backend.app.database.session import Base, engine, SessionLocal  # noqa: E402
from backend.app.database import models                      # noqa: E402
from backend.app.api import titan                            # noqa: E402
from backend.app.ai_agents import tutor_agent                # noqa: E402
from backend.app.database.seed_titan import seed_titan       # noqa: E402

# Hard guarantee: no provider calls during QA.
tutor_agent.call_claude_json = lambda *a, **k: None


# ── Tiny assertion harness ──
_RESULTS = []


def check(name, cond, detail=""):
    _RESULTS.append((name, bool(cond), detail))
    flag = "PASS" if cond else "FAIL"
    print(f"  [{flag}] {name}" + (f" — {detail}" if detail and not cond else ""))
    return cond


def build_client():
    Base.metadata.create_all(bind=engine)
    app = FastAPI()
    app.include_router(titan.router)
    app.include_router(titan.dashboard_router)
    return TestClient(app)


def run():
    print("Titan Track QA harness\n" + "=" * 50)

    # Confirm provider is truly disabled.
    from backend.app.config import settings
    check("api_keys_blanked", not settings.ANTHROPIC_API_KEY,
          f"anthropic={'set' if settings.ANTHROPIC_API_KEY else 'empty'}")

    client = build_client()
    db = SessionLocal()
    seed_report = seed_titan(db)
    check("seed_ran", seed_report.get("seeded") is True, str(seed_report))

    # ── Tracks ──
    r = client.get("/api/titan/tracks")
    check("tracks_200", r.status_code == 200, f"status={r.status_code}")
    tracks = r.json()
    check("tracks_count_6", len(tracks) == 6, f"got {len(tracks)}")
    horizon = [t for t in tracks if t["target_tier"] == "horizon"]
    check("one_horizon_track", len(horizon) == 1, f"got {len(horizon)}")

    # ── Modules ──
    r = client.get("/api/titan/modules", params={"tier": "now"})
    now_modules = r.json()
    check("now_modules_exist", len(now_modules) >= 20, f"got {len(now_modules)}")
    check("modules_no_extra_data", all("extra_data" not in m for m in now_modules),
          "extra_data leaked")

    # Find Track A entry module (A1, available, no prereqs)
    a1 = next((m for m in now_modules if m["phase_code"] == "A1"), None)
    a2 = next((m for m in now_modules if m["phase_code"] == "A2"), None)
    check("a1_available", a1 and a1["status"] == "available", a1["status"] if a1 else "missing")
    check("a2_locked", a2 and a2["status"] == "locked", a2["status"] if a2 else "missing")

    # Module detail + prerequisite chain
    r = client.get(f"/api/titan/modules/{a2['id']}")
    detail = r.json()
    check("a2_prereq_chain", len(detail.get("prerequisite_chain", [])) == 1,
          str(detail.get("prerequisite_chain")))

    # ── Session today: answer key must not leak ──
    r = client.get("/api/titan/session/today")
    check("session_200", r.status_code == 200, f"status={r.status_code}")
    sess = r.json()
    content = (sess.get("payload") or {}).get("content") or {}
    check("session_has_quiz", isinstance(content.get("quiz"), list) and len(content["quiz"]) >= 3,
          f"quiz len={len(content.get('quiz') or [])}")
    leaked = "_quiz_key" in content or any("answer_index" in (q or {}) for q in (content.get("quiz") or []))
    check("answer_key_not_leaked", not leaked, "answer key exposed in session payload")
    check("session_has_diagram", isinstance(content.get("diagram"), dict)
          and (content["diagram"].get("nodes") or content["diagram"].get("columns")),
          "diagram missing/empty")
    check("session_has_explain_prompt", bool((content.get("explain_back_prompt") or "").strip()),
          "explain-back prompt missing")
    check("confidence_surfaced", bool(content.get("confidence_note")), "confidence note missing")

    # ── Get-or-create is idempotent; the date unique constraint stops races ──
    s_again = tutor_agent.TutorAI(db).get_daily_session()
    check("session_get_idempotent", s_again["id"] == sess["id"], f"{s_again['id']} vs {sess['id']}")
    from sqlalchemy.exc import IntegrityError as _IE
    db.add(models.DailySession(date=sess["date"], session_payload={}))
    try:
        db.commit()
        check("session_date_unique", False, "duplicate session for same date was allowed")
    except _IE:
        db.rollback()
        check("session_date_unique", True)

    # ── Gate enforcement: explain-back before quiz must 409 ──
    r = client.post(f"/api/titan/modules/{a1['id']}/explain-back",
                    json={"transcript": "x", "prior_attempts": 0})
    check("explain_before_quiz_blocked", r.status_code == 409, f"status={r.status_code}")

    # ── Manual 'mastered' must be rejected ──
    r = client.patch(f"/api/titan/modules/{a1['id']}", json={"status": "mastered"})
    check("manual_master_blocked", r.status_code == 400, f"status={r.status_code}")

    # ── Quiz attempt with correct answers (read key white-box) ──
    tutor = tutor_agent.TutorAI(db)
    gen = tutor.generate_module_content(a1["id"])
    key = gen.get("_quiz_key") or []
    correct_answers = [e.get("answer_index", 0) for e in key]
    r = client.post(f"/api/titan/modules/{a1['id']}/attempt", json={"answers": correct_answers})
    grade = r.json()
    check("attempt_scored_100", grade.get("score") == 100, f"score={grade.get('score')}")
    check("attempt_passed_quiz", grade.get("passed_quiz") is True, str(grade.get("passed_quiz")))
    check("next_step_explain", grade.get("next_step") == "explain_back", str(grade.get("next_step")))

    # Wrong answers -> below threshold
    wrong = [(a + 1) % 4 for a in correct_answers]
    r = client.post(f"/api/titan/modules/{a1['id']}/attempt", json={"answers": wrong})
    check("wrong_answers_low_score", r.json().get("score", 100) < 80, f"score={r.json().get('score')}")

    # Re-pass quiz so latest attempt clears the gate again
    client.post(f"/api/titan/modules/{a1['id']}/attempt", json={"answers": correct_answers})

    # ── Explain-back pass -> mastery + unlock ──
    long_transcript = (
        "Retrieval practice means actively pulling information from memory instead of "
        "re-reading it, and spacing means revisiting it at expanding intervals. The reason "
        "it works is that the effort of recall strengthens the memory trace far more than "
        "passive review, and spacing forces repeated effortful retrievals over time, which "
        "is why this module is tagged strong evidence for retention even if far transfer is weaker."
    )
    r = client.post(f"/api/titan/modules/{a1['id']}/explain-back",
                    json={"transcript": long_transcript, "prior_attempts": 0})
    eb = r.json()
    check("explain_back_passed", eb.get("passed") is True, str(eb))
    check("module_mastered", eb.get("module_mastered") is True, str(eb.get("module_mastered")))
    check("a2_unlocked", a2["id"] in (eb.get("unlocked_module_ids") or []),
          f"unlocked={eb.get('unlocked_module_ids')}")

    # Track A progress should now be > 0
    r = client.get("/api/titan/tracks")
    track_a = next((t for t in r.json() if t["code"] == "A"), None)
    check("track_a_progress", track_a and track_a["progress_pct"] > 0,
          f"pct={track_a['progress_pct'] if track_a else 'n/a'}")

    # Mastery history records both attempts
    r = client.get(f"/api/titan/modules/{a1['id']}/mastery-history")
    check("mastery_history", len(r.json()) >= 1, f"entries={len(r.json())}")

    # ── Streak: start + complete today's session ──
    sid = sess["id"]
    r = client.post(f"/api/titan/session/{sid}/start", json={"energy_level": "high"})
    check("session_start", r.status_code == 200 and r.json().get("started"), str(r.json()))
    r = client.post(f"/api/titan/session/{sid}/complete", json={"minutes_spent": 25})
    comp = r.json()
    check("session_complete", comp.get("completed") is True, str(comp))
    check("streak_incremented", comp.get("streak", {}).get("current_streak", 0) >= 1,
          str(comp.get("streak")))
    check("heatmap_present", len(comp.get("streak", {}).get("heatmap", [])) == 182,
          f"cells={len(comp.get('streak', {}).get('heatmap', []))}")
    # Completing twice must be idempotent (no double minutes / re-streak).
    r = client.post(f"/api/titan/session/{sid}/complete", json={"minutes_spent": 99})
    check("complete_idempotent", r.json().get("already_completed") is True, str(r.json()))

    # ── Reps sync — exercise the enum-filtered query with a REAL row ──
    # (validates the Postgres-safe enum-member filter, not just the empty path)
    db.add(models.Lead(name="QA Prospect", company="Acme", status=models.LeadStatus.CONTACTED,
                       notes="Discussed pricing on a call."))
    db.add(models.Project(name="QA Project", status=models.TaskStatus.IN_PROGRESS))
    db.commit()
    r = client.post("/api/titan/reps/sync")
    check("reps_sync_ok", r.status_code == 200, f"status={r.status_code}")
    check("reps_sync_created", r.json().get("created", 0) >= 1, f"created={r.json().get('created')}")
    # The synced rep must carry an AI (here: deterministic-fallback) after-action review.
    reps = client.get("/api/titan/reps").json()
    check("synced_rep_has_review", any(rp.get("ai_after_action_review") for rp in reps),
          "no after-action review on synced rep")
    # Idempotency: a second sync must not duplicate.
    r2 = client.post("/api/titan/reps/sync")
    check("reps_sync_idempotent", r2.json().get("created", 99) == 0, f"created={r2.json().get('created')}")

    # Create a manual rep directly, then reflect on it
    rep = models.LeadershipRep(source_type="manual", description="Mock pitch call",
                               ai_after_action_review="You named the ask late.",
                               presence_score=60.0)
    db.add(rep)
    db.commit()
    db.refresh(rep)
    r = client.post(f"/api/titan/reps/{rep.id}/reflect",
                    json={"reflection": "I hesitated on price."})
    check("rep_reflect", r.status_code == 200 and r.json().get("user_reflection"), str(r.json()))

    # ── Roadmap + snapshot + history ──
    r = client.get("/api/titan/roadmap")
    rm = r.json()
    check("roadmap_now_horizon", len(rm.get("now", [])) == 5 and len(rm.get("horizon", [])) == 1,
          f"now={len(rm.get('now', []))} horizon={len(rm.get('horizon', []))}")
    check("compass_note_present", bool(rm.get("compass_note")), "compass note missing")
    r = client.post("/api/titan/roadmap/snapshot", json={"change_note": "qa snapshot"})
    check("snapshot_saved", r.status_code == 200 and r.json().get("version", 0) >= 2,
          str(r.json().get("version")))
    r = client.get("/api/titan/roadmap/history")
    check("roadmap_history", len(r.json()) >= 2, f"versions={len(r.json())}")

    # ── Feedback (QA Layer 4) ──
    r = client.post(f"/api/titan/session/{sid}/feedback",
                    json={"module_id": a1["id"], "thumbs": "down"})
    check("feedback_logged", r.status_code == 200 and r.json().get("logged"), str(r.json()))

    # ── Dashboard aggregation (v2 contract: today_lessons/active_projects/
    #    upcoming_test replaced the old single today_session) ──
    r = client.get("/api/dashboard/titan-track")
    dash = r.json()
    check("dashboard_200", r.status_code == 200, f"status={r.status_code}")
    check("dashboard_shape",
          all(k in dash for k in ("streak", "now_tracks", "horizon_tracks",
                                  "today_lessons", "active_projects", "upcoming_test")),
          f"keys={list(dash.keys())}")

    db.close()


def main():
    try:
        run()
    except Exception:
        print("\nHARNESS CRASHED:")
        traceback.print_exc()
        _RESULTS.append(("harness_crash", False, "exception"))

    passed = sum(1 for _, ok, _ in _RESULTS if ok)
    total = len(_RESULTS)
    failed = [(n, d) for n, ok, d in _RESULTS if not ok]
    print("\n" + "=" * 50)
    print(f"RESULT: {passed}/{total} checks passed")
    if failed:
        print("FAILURES:")
        for n, d in failed:
            print(f"  - {n}: {d}")
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
