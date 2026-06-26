"""
Frozen Titan Track course content.

Loads pre-authored lesson content (concept, big picture, historical example,
modern practice, diagram, exercises, quiz + answer key, explain-back prompt,
project brief) keyed by module phase_code (A1, B2, C3, ...). This is the source
of truth for lessons so they are instant and stable — the Tutor AI only
generates content as a fallback for a module that has no authored lesson yet.

Regenerate the JSON with:  python -m backend.bake_titan_content
"""

from __future__ import annotations

import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "titan_content.json")

try:
    with open(_PATH, encoding="utf-8") as _f:
        TITAN_CONTENT = json.load(_f)
except Exception:
    TITAN_CONTENT = {}
