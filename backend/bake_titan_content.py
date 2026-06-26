"""
One-time course "bake": generate the full lesson content for every Titan Track
module via the Tutor AI and freeze it to ``app/database/titan_content.json``.

After this runs, lessons are served from the frozen file (instant + stable) and
the AI is no longer called to author content at runtime — it just grades your
explain-backs / projects and helps on demand.

Run:  python -m backend.bake_titan_content
Re-run any time you want to refresh the authored course.
"""

import os
import json
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
from backend.app.ai_agents.tutor_agent import TutorAI  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(__file__), "app", "database", "titan_content.json")


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_titan(db)  # idempotent — ensures modules exist
        tutor = TutorAI(db)
        modules = db.query(models.LearningModule).order_by(models.LearningModule.id).all()

        # Start from whatever is already baked so a re-run can be incremental.
        out = {}
        if os.path.exists(OUT_PATH):
            try:
                with open(OUT_PATH, encoding="utf-8") as f:
                    out = json.load(f)
            except Exception:
                out = {}

        total = len(modules)
        for i, m in enumerate(modules, 1):
            print(f"[{i}/{total}] baking {m.phase_code} — {m.title} ...", flush=True)
            content = tutor.generate_module_content(m.id, force=True)
            if isinstance(content, dict) and "error" not in content:
                content.pop("_structural_reason", None)
                out[m.phase_code] = content
                # Write after each module so a crash/rate-limit doesn't lose progress.
                with open(OUT_PATH, "w", encoding="utf-8") as f:
                    json.dump(out, f, ensure_ascii=False, indent=1)
            else:
                print(f"   !! failed: {content}", flush=True)

        print(f"\nDONE — wrote {len(out)} modules to {OUT_PATH}", flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
