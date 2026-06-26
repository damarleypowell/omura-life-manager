"""Shared serialization helpers."""
from typing import Any


def strip_internal_keys(obj: Any) -> Any:
    """Recursively drop ``_``-prefixed dict keys so agent internals — e.g. the
    quiz answer key ``_quiz_key`` or a negotiation counterpart's hidden
    ``_counterpart_position`` — never leave the process through any client- or
    LLM-facing surface (the generic ``/api/ai/execute`` dispatcher and the
    supervisor chat tool loop both run results through this). Lists are
    recursed; non-container values pass through untouched.
    """
    if isinstance(obj, dict):
        return {k: strip_internal_keys(v) for k, v in obj.items()
                if not (isinstance(k, str) and k.startswith("_"))}
    if isinstance(obj, list):
        return [strip_internal_keys(v) for v in obj]
    return obj
