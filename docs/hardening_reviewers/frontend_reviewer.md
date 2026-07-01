# Frontend / UX Reviewer — IMMUTABLE

Frozen on creation. Evidence-anchored (cite `file:line`). Treats silent failures
and confusing output as bugs, not nits.

## Scope
`frontend/src/components/Dashboard/*`, `components/Shared/*`,
`services/apiService.js`, `pages/index.jsx`. `npx next build` must pass.

## Mandatory sweep
- **No raw JSON to the user.** Agent/workflow/insight output must render as
  English prose, never `{...}` braces. (User requirement.)
- **Error visibility:** every fetch/axios call surfaces failure to the user
  (toast or inline), never a silent `catch {}` or a dead button.
- **Resilience to data:** guards for undefined/empty (no leads, no session,
  null fields); loading + empty + error states present; never throws on partial
  payloads.
- **State correctness:** component state resets when its underlying entity
  changes (keyed remounts); no stale status after a reload.
- **Accessibility:** interactive controls keyboard-operable + labeled; quiz/radio
  semantics; toggles have aria state.
- **Build + console:** `next build` green; no obvious runtime console errors; no
  in-render mutation of memoized/prop arrays.

## Hard kill-criteria
- Raw JSON shown to the user → high (violates explicit requirement).
- Crash on a normal/partial payload, or build fails → critical.
- A button that errors into the void with no feedback → high.

## Pass bar
Score ≥ 95, zero open critical/high/medium, `next build` green.
