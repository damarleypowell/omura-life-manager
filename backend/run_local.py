"""
Local dev runner — boots Omura against a throwaway local SQLite DB so a
``localhost`` run never touches the production Neon database, while still loading
the real API keys from ``backend/.env`` so the Claude-powered agents (Tutor on
Sonnet) work.

Run:  uvicorn backend.run_local:app --host 127.0.0.1 --port 8003
"""

import os
import dotenv
from dotenv import dotenv_values

# 1) Pick the local DB BEFORE any app import:
#    - if LOCAL_DATABASE_URL is set (shell env or backend/.env) -> use it
#      (your local Postgres), e.g. postgresql://postgres:pw@localhost:5432/omura
#    - otherwise fall back to a throwaway local SQLite file.
_repo_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_env_vals = dotenv_values(_repo_env)
_local_db = os.environ.get("LOCAL_DATABASE_URL") or _env_vals.get("LOCAL_DATABASE_URL")
os.environ["DATABASE_URL"] = _local_db or "sqlite:///./omura_local.db"
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/0")
print(f"[run_local] DB = {'local Postgres' if _local_db else 'SQLite (omura_local.db)'}", flush=True)

# 2) Load the real keys from .env WITHOUT clobbering DATABASE_URL above.
dotenv.load_dotenv(_repo_env, override=False)

# 3) Neutralize main.py's own override=True load so it cannot restore the
#    production DATABASE_URL from .env on import.
_orig_load = dotenv.load_dotenv
dotenv.load_dotenv = lambda *a, **k: _orig_load(*a, **{**k, "override": False})

# 3b) Local Google OAuth: point the redirect + post-login redirect at localhost so
#     "Connect Google" completes against this machine (otherwise it bounces to the
#     production callback). NOTE: also add this exact redirect URI to your Google
#     Cloud Console → Credentials → Authorized redirect URIs. setdefault means a
#     value already in backend/.env wins.
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:8003/auth/google/callback")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3001")

# 4) Now import the app — triggers config, table create_all, and the Titan seed
#    against local SQLite.
from backend.app.main import app  # noqa: E402,F401
