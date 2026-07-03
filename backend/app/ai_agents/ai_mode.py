"""
Runtime AI mode — run Omura on the cloud (Claude) or fully offline on the local
Ollama model, toggled live from the UI. Persisted to a small file in the user's
home (NOT under backend/, so flipping it never trips the dev auto-reloader) so
the choice survives a backend restart.

Modes:
  online  — always use cloud Claude (needs internet + ANTHROPIC_API_KEY)
  offline — always use the local Ollama model (no internet; uses your local 7B)
  auto    — prefer cloud, fall back to the local model when the cloud is
            unreachable (best of both when the connection is flaky)
"""

from __future__ import annotations

import os

_STATE_FILE = os.path.join(os.path.expanduser("~"), ".omura_ai_mode")
_VALID = ("online", "offline", "auto")
_mode: str | None = None


def _load() -> str:
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            m = f.read().strip().lower()
            if m in _VALID:
                return m
    except Exception:
        pass
    env = (os.environ.get("OMURA_AI_MODE") or "auto").strip().lower()
    return env if env in _VALID else "auto"


def get_mode() -> str:
    global _mode
    if _mode is None:
        _mode = _load()
    return _mode


def set_mode(m: str) -> str:
    global _mode
    m = (m or "").strip().lower()
    if m not in _VALID:
        raise ValueError(f"mode must be one of {_VALID}")
    _mode = m
    try:
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            f.write(m)
    except Exception:
        pass
    return _mode
