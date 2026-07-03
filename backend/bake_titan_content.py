"""
One-time course "bake": author the full lesson content for every Titan Track
module and freeze it to ``app/database/titan_content.json``.

Every lesson goes through the STRICT QA pipeline (deterministic auditor +
harsh LLM examiner + revision loop) and is regenerated with the examiner's
notes until it clears the quality bar (default 95) or attempts run out — the
best draft wins. After this runs, lessons are pre-made: served instantly from
the frozen file, stable day to day. The AI only re-authors near-term lessons
on demand (the bounded /refresh path) — it never rewrites the frozen course.

Run:  python -m backend.bake_titan_content
Env:  TITAN_BAKE_TARGET=95        quality bar (set 0 to skip the QA loop)
      TITAN_BAKE_ATTEMPTS=3       max generation attempts per lesson
      TITAN_BAKE_ONLY=P1A,P2B     optional: bake only these phase_codes
Re-run any time you want to refresh the authored course; it is incremental
(already-baked v3 modules that passed the bar are skipped unless forced).
"""

import os
import json
import time
import dotenv
from dotenv import dotenv_values

# Use the local DB + real API keys (mirrors run_local) so the bake never touches
# the production database but can still call the Tutor (Sonnet).
_repo_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_env_vals = dotenv_values(_repo_env)
_local_db = os.environ.get("LOCAL_DATABASE_URL") or _env_vals.get("LOCAL_DATABASE_URL")
os.environ["DATABASE_URL"] = _local_db or "sqlite:///./omura_local.db"
dotenv.load_dotenv(_repo_env, override=False)

from backend.app.database.session import SessionLocal, engine, Base  # noqa: E402
from backend.app.database import models  # noqa: E402
from backend.app.database.seed_titan import seed_titan  # noqa: E402
from backend.app.ai_agents.tutor_agent import (  # noqa: E402
    TutorAI, CONTENT_SCHEMA_VERSION, STRICT_QA_TARGET, STRICT_QA_MAX_ATTEMPTS,
)

OUT_PATH = os.path.join(os.path.dirname(__file__), "app", "database", "titan_content.json")


def main() -> None:
    target = int(os.environ.get("TITAN_BAKE_TARGET", str(STRICT_QA_TARGET)))
    attempts = int(os.environ.get("TITAN_BAKE_ATTEMPTS", str(STRICT_QA_MAX_ATTEMPTS)))
    only = {c.strip() for c in os.environ.get("TITAN_BAKE_ONLY", "").split(",") if c.strip()}

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_titan(db)  # idempotent — ensures modules exist
        tutor = TutorAI(db)
        modules = db.query(models.LearningModule).order_by(models.LearningModule.id).all()
        if only:
            modules = [m for m in modules if m.phase_code in only]

        # Start from whatever is already baked so a re-run can be incremental.
        out = {}
        if os.path.exists(OUT_PATH):
            try:
                with open(OUT_PATH, encoding="utf-8") as f:
                    out = json.load(f)
            except Exception:
                out = {}

        total = len(modules)
        t0 = time.time()
        for i, m in enumerate(modules, 1):
            existing = out.get(m.phase_code) or {}
            if (int(existing.get("_schema_version", 0)) >= CONTENT_SCHEMA_VERSION
                    and (existing.get("_qa_overall") or 0) >= target):
                print(f"[{i}/{total}] {m.phase_code} — already baked at "
                      f"QA {existing.get('_qa_overall')} — skip", flush=True)
                continue

            print(f"[{i}/{total}] baking {m.phase_code} — {m.title} ...", flush=True)
            if target > 0:
                report = tutor.generate_to_standard(m.id, target=target, max_attempts=attempts)
                content = report.get("content")
                trail = " -> ".join(str(a["overall"]) for a in report.get("attempts", []))
                status = "PASS" if report.get("passed") else "BEST-EFFORT"
                print(f"   QA {status}: {trail} (bar {target})", flush=True)
            else:
                content = tutor.generate_module_content(m.id, force=True)

            if isinstance(content, dict) and content and "error" not in content:
                content = dict(content)
                content.pop("_structural_reason", None)
                out[m.phase_code] = content
                # Write after each module so a crash/rate-limit doesn't lose progress.
                with open(OUT_PATH, "w", encoding="utf-8") as f:
                    json.dump(out, f, ensure_ascii=False, indent=1)
            else:
                print(f"   !! failed: {content}", flush=True)

        mins = (time.time() - t0) / 60
        print(f"\nDONE — wrote {len(out)} modules to {OUT_PATH} in {mins:.1f} min", flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
