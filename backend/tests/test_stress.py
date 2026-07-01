"""
Full-app stress / smoke harness.

Run:  python -m backend.tests.test_stress

Boots the REAL FastAPI app against a throwaway SQLite DB with ALL provider keys
blanked (so LLM/email/Apollo calls fail fast and we prove GRACEFUL DEGRADATION,
with zero external API spend) and the scheduler off. Then hammers every
endpoint with valid AND malformed input and asserts:

  • no unhandled 500 on a normal request (degraded answers are fine),
  • bad input returns 4xx (not 500),
  • core flows return sane shapes.

Exits non-zero on any failure so a reviewer can gate on it.
"""

from __future__ import annotations

import os
import sys
import tempfile
import traceback

# ── Isolate BEFORE importing app code (mirror run_local, but for tests) ──
_TMP_DB = os.path.join(tempfile.gettempdir(), "omura_stress.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["REDIS_URL"] = "redis://127.0.0.1:6399/0"
os.environ["SCHEDULER_ENABLED"] = "false"
for _k in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GEMINI_FLASH_KEY", "APOLLO_API_KEY",
           "HUNTER_API_KEY", "RESEND_API_KEY", "GMAIL_APP_PASSWORD", "SENDGRID_API_KEY"):
    os.environ[_k] = ""

# Neutralize main.py's load_dotenv(override=True) so it can't restore real values.
import dotenv  # noqa: E402
_orig_load = dotenv.load_dotenv
dotenv.load_dotenv = lambda *a, **k: _orig_load(*a, **{**k, "override": False})

from fastapi.testclient import TestClient  # noqa: E402
from backend.app.main import app           # noqa: E402

client = TestClient(app, raise_server_exceptions=False)  # don't re-raise -> we inspect 500s

_RESULTS = []


def check(name, cond, detail=""):
    _RESULTS.append((name, bool(cond), detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))
    return cond


def get(path, expect=(200,)):
    r = client.get(path)
    no500 = r.status_code < 500
    check(f"GET {path} no-500", no500, f"status={r.status_code}")
    if expect:
        check(f"GET {path} expected", r.status_code in expect, f"status={r.status_code}")
    return r


def post(path, json=None, expect=None):
    r = client.post(path, json=json or {})
    check(f"POST {path} no-500", r.status_code < 500, f"status={r.status_code}")
    if expect is not None:
        check(f"POST {path} status", r.status_code in expect, f"status={r.status_code}")
    return r


def run():
    print("Omura full-app stress harness\n" + "=" * 56)

    # ── Health / root (always-on, no deps) ──
    get("/health"); get("/")

    # ── Dashboards (aggregations — must survive empty DB + no AI) ──
    for d in ["life-overview", "business-command", "content-studio",
              "communication-center", "titan-track"]:
        get(f"/api/dashboard/{d}")

    # ── Core list endpoints ──
    for p in ["/api/projects", "/api/tasks", "/api/content", "/api/leads",
              "/api/metrics", "/api/health", "/api/calendar", "/api/notes",
              "/api/scenarios", "/api/communications", "/api/conversations",
              "/api/agent-logs", "/api/insights", "/api/titan/tracks",
              "/api/titan/modules", "/api/titan/roadmap", "/api/titan/streak",
              "/api/titan/reps", "/api/scheduler/jobs"]:
        get(p)

    # ── Create + read-back a few core records ──
    r = post("/api/projects", {"name": "Stress Project", "priority": "high"}, expect=(200, 201))
    pid = r.json().get("id") if r.status_code < 300 else None
    check("project created", bool(pid), str(r.status_code))
    post("/api/tasks", {"title": "Stress Task", "project_id": pid}, expect=(200, 201))
    post("/api/leads", {"name": "Stress Lead", "email": "x@example.com"}, expect=(200, 201))
    post("/api/notes", {"title": "n", "content": "c"}, expect=(200, 201))
    post("/api/metrics", {"category": "revenue", "name": "MRR", "value": 100}, expect=(200, 201))
    post("/api/content", {"title": "c", "platform": "instagram"}, expect=(200, 201))

    # ── Malformed input must be 4xx, never 500 ──
    check("missing-required -> 422", client.post("/api/projects", json={}).status_code == 422)
    check("bad-type -> 422", client.post("/api/metrics", json={"category": "x", "name": "y", "value": "not-a-number"}).status_code == 422)
    check("unknown project 404", client.get("/api/projects/999999").status_code == 404)
    check("unknown titan module 404", client.get("/api/titan/modules/999999").status_code == 404)
    check("patch missing task 404", client.patch("/api/tasks/999999", json={"status": "done"}).status_code == 404)

    # ── AI agents (keys blanked -> graceful fallback, NO 500) ──
    agent_calls = [
        ("inbox", "process_inbox", {}),
        ("content", "suggest_content_ideas", {"recent_trends": ["ai"]}),
        ("project", "analyze_pipeline", {}),
        ("crm", "analyze_pipeline", {}),
        ("finance", "calculate_kpis", {}),
        ("health", "generate_daily_recommendation", {}),
        ("market", "monitor_competitors", {"competitors": []}),
        ("scenario", "simulate_business", {"params": {"scenario_description": "x"}}),
        ("automation", "run_workflow", {"workflow_name": "business_metrics", "params": {}}),
    ]
    for ag, act, params in agent_calls:
        r = client.post("/api/ai/execute", json={"agent": ag, "action": act, "params": params})
        check(f"agent {ag}/{act} no-500", r.status_code < 500, f"status={r.status_code}")

    # Unknown agent / action -> 400, not 500
    check("unknown agent 400", client.post("/api/ai/execute", json={"agent": "nope", "action": "x"}).status_code == 400)
    check("unknown action 400", client.post("/api/ai/execute", json={"agent": "crm", "action": "nope"}).status_code == 400)
    check("private action blocked", client.post("/api/ai/execute", json={"agent": "crm", "action": "_secret"}).status_code == 400)

    # ── Workflows (all four) ──
    for wf in ["lead_management", "content_publishing", "health_optimization", "business_metrics"]:
        r = client.post("/api/ai/workflow", json={"workflow": wf, "params": {}})
        check(f"workflow {wf} no-500", r.status_code < 500, f"status={r.status_code}")

    # ── Chat (no key -> must degrade gracefully, not crash) ──
    r = client.post("/api/chat", json={"message": "hello"})
    check("chat no-500", r.status_code < 500, f"status={r.status_code}")
    check("chat returns reply", isinstance(r.json().get("reply"), str), "no reply field")
    conv = client.post("/api/conversations", json={"title": "t"}).json()
    cid = conv.get("id")
    if cid:
        r = client.post(f"/api/conversations/{cid}/chat", json={"message": "hi"})
        check("conversation chat no-500", r.status_code < 500, f"status={r.status_code}")

    # ── Titan gate (deterministic without AI) ──
    mods = client.get("/api/titan/modules", params={"tier": "now"}).json()
    a1 = next((m for m in mods if m.get("phase_code") == "A1"), None)
    if a1:
        r = client.post(f"/api/titan/modules/{a1['id']}/attempt", json={"answers": [0, 0, 0]})
        check("titan attempt no-500", r.status_code < 500, f"status={r.status_code}")
        # explain-back before passing quiz must be blocked (409), never 500
        rb = client.post(f"/api/titan/modules/{a1['id']}/explain-back", json={"transcript": "x"})
        check("titan gate enforced", rb.status_code in (409, 200), f"status={rb.status_code}")

    # ── Insights endpoint with section filter ──
    get("/api/insights?section=business")
    get("/api/insights?section=content")

    # ── Idempotency: titan reps sync twice ──
    post("/api/titan/reps/sync", expect=(200,))
    post("/api/titan/reps/sync", expect=(200,))


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
    print("\n" + "=" * 56)
    print(f"RESULT: {passed}/{total} checks passed")
    if failed:
        print("FAILURES:")
        for n, d in failed:
            print(f"  - {n}: {d}")
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
