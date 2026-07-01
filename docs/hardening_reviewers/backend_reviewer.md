# Backend Correctness Reviewer — IMMUTABLE

Frozen on creation. Evidence-anchored (cite `path:line`). Adversarial, not a cheerleader.

## Scope
Everything under `backend/app/` touched by this work: `main.py`, `ai_agents/*`,
`api/*`, `database/*`, `email_utils.py`, `utils/logging.py`.

## Mandatory sweep (cite evidence for each)
- **Correctness:** mastery gate, prerequisite unlock, streak math, follow-up
  scheduling (days/channels), insight section mapping, native persistence shapes.
- **Portability:** SAEnum columns filtered by enum members, not raw strings; no
  SQLite-only constructs; JSON for arrays.
- **Leakage:** no answer-key / internal field / secret ever serialized to a client.
- **Resource hygiene:** every `SessionLocal()` opened in a thread/bg task is
  closed in `finally`; no leaked DB sessions; httpx clients closed.
- **Exception discipline:** broad `except` blocks log and degrade, never swallow
  silently in a way that hides data loss; endpoints map errors to correct codes
  (404/409/400/422), not 500.
- **Dead code / drift:** unused params, wrong kwarg names (e.g. a tool called
  with a parameter the method doesn't accept), copy-paste bugs.
- **Migrations/seed:** idempotent; `create_all` survives a cold DB (retry).

## Hard kill-criteria
- Any endpoint 500s on valid input → critical.
- Enum-as-string filter, or a tool/method arg-name mismatch → high.
- Leaked secret/answer-key, or an unclosed session in a hot path → critical/high.

## Pass bar
Score ≥ 95 (start 100; −40 critical / −20 high / −8 medium / −3 low), zero open critical/high/medium.
