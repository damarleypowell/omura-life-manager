"""
Shared AI caller for all Omura worker agents.

Claude only (Anthropic). Gemini has been fully removed. The model defaults to
Haiku for worker agents and is overridable via settings.OMURA_WORKER_MODEL or a
per-call ``model`` argument (the Tutor uses Sonnet).
"""

from __future__ import annotations

import json
import os
import re
import time
import traceback
import urllib.request
from typing import Any, Optional

from backend.app.config import settings
from backend.app.ai_agents import ai_mode
from backend.app.utils.logging import OmuraLogger

_logger = OmuraLogger("ai_caller")

ANTHROPIC_MODEL = settings.OMURA_WORKER_MODEL
OLLAMA_MODEL = os.environ.get("OMURA_OLLAMA_MODEL", "qwen2.5:7b")

# Lazy-initialized client
_anthropic_client = None


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None and settings.ANTHROPIC_API_KEY:
        import anthropic
        # Explicit bounded per-request timeout so a hung edge can't stall a
        # synchronous FastAPI request. max_retries=0 — this module owns the
        # retry/fallback policy (the [0,15,45]s loop across models below), so we
        # don't want the SDK silently stacking its own retries on top.
        _anthropic_client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=90.0,
            max_retries=0,
        )
    return _anthropic_client


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("429", "quota", "resource_exhausted", "rate_limit", "rate limit", "overloaded", "529"))


def _call_anthropic(prompt: str, system_prompt: str, agent_name: str, temperature: float, max_tokens: int, model: Optional[str] = None) -> Optional[str]:
    client = _get_anthropic()
    if not client:
        return None
    use_model = model or ANTHROPIC_MODEL
    # Try the requested model; if it keeps failing/overloading and it isn't the
    # fast default, fall back to the default model so a hiccup ≠ a hard error.
    models_to_try = [use_model]
    if use_model != ANTHROPIC_MODEL:
        models_to_try.append(ANTHROPIC_MODEL)

    for mi, m in enumerate(models_to_try):
        for attempt, delay in enumerate([0, 15, 45]):
            if delay:
                _logger.warning(f"[{agent_name}] {m} busy — retrying in {delay}s")
                time.sleep(delay)
            try:
                if max_tokens > 4096:
                    # Long generations (e.g. 16k-token deep lessons) MUST
                    # stream: a synchronous request that takes minutes hits the
                    # 90s client timeout and then silently falls back to the
                    # fast model — a whole course quietly authored by Haiku.
                    # Streaming keeps bytes flowing, so the timeout only
                    # applies between chunks, never to the total duration.
                    with client.messages.stream(
                        model=m,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=system_prompt,
                        messages=[{"role": "user", "content": prompt}],
                    ) as stream:
                        text = "".join(stream.text_stream)
                    if mi > 0:
                        _logger.warning(f"[{agent_name}] fell back to {m}")
                    return text
                response = client.messages.create(
                    model=m,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                )
                if mi > 0:
                    _logger.warning(f"[{agent_name}] fell back to {m}")
                return response.content[0].text
            except Exception as exc:
                if _is_rate_limit(exc) and attempt < 2:
                    continue
                _logger.error(f"[{agent_name}] Anthropic error on {m}: {exc}")
                break  # give up on this model, try the fallback (if any)
    return None


def _call_ollama(prompt: str, system_prompt: str, agent_name: str, temperature: float, max_tokens: int) -> Optional[str]:
    """Call the local Ollama model (fully offline, no internet). Raw text or None."""
    url = settings.OLLAMA_BASE_URL.rstrip("/") + "/api/chat"
    body = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        # Generous timeout: a cold 7B on CPU can take ~30s on the first call
        # (model load) before it's warm.
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (data.get("message") or {}).get("content") or None
    except Exception as exc:  # noqa: BLE001 — offline model unreachable → None
        _logger.error(f"[{agent_name}] Ollama error: {exc}")
        return None


def call_claude(
    prompt: str,
    system_prompt: str,
    agent_name: str = "agent",
    temperature: float = 0.3,
    max_tokens: int = 2048,
    model: Optional[str] = None,
) -> Optional[str]:
    """Call Claude and return raw text (None if unavailable after retries).

    ``model`` optionally overrides the default worker model (Haiku) for a single
    call — e.g. the Tutor uses Sonnet for richer lesson generation.

    Routed by the runtime AI mode: 'online' → cloud Claude, 'offline' → local
    Ollama model, 'auto' → cloud with an automatic local fallback.
    """
    mode = ai_mode.get_mode()
    if mode == "offline":
        result = _call_ollama(prompt, system_prompt, agent_name, temperature, max_tokens)
    elif mode == "online":
        result = _call_anthropic(prompt, system_prompt, agent_name, temperature, max_tokens, model)
    else:  # auto — prefer cloud, fall back to the local model when it's unreachable
        result = _call_anthropic(prompt, system_prompt, agent_name, temperature, max_tokens, model)
        if result is None:
            _logger.warning(f"[{agent_name}] cloud unavailable — falling back to local model")
            result = _call_ollama(prompt, system_prompt, agent_name, temperature, max_tokens)

    if result is not None:
        _logger.debug(f"[{agent_name}] AI call successful ({len(result)} chars, mode={mode})")
    else:
        _logger.warning(f"[{agent_name}] AI call returned no result (mode={mode})")
    return result


def call_claude_json(
    prompt: str,
    system_prompt: str,
    agent_name: str = "agent",
    temperature: float = 0.3,
    max_tokens: int = 2048,
    model: Optional[str] = None,
) -> Optional[dict]:
    """Call AI and parse response as JSON. ``model`` optionally overrides the
    default Anthropic model for this call."""
    raw = call_claude(
        prompt=prompt,
        system_prompt=system_prompt,
        agent_name=agent_name,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
    )
    if raw is None:
        return None
    return _parse_json_response(raw, agent_name)


def _parse_json_response(text: str, agent_name: str = "agent") -> Optional[dict]:
    if not text:
        return None
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    if "```" in text:
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

    brace_start = text.find('{')
    bracket_start = text.find('[')

    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start:i + 1])
                    except json.JSONDecodeError:
                        break

    if bracket_start >= 0 and (brace_start < 0 or bracket_start < brace_start):
        depth = 0
        for i in range(bracket_start, len(text)):
            if text[i] == '[':
                depth += 1
            elif text[i] == ']':
                depth -= 1
                if depth == 0:
                    try:
                        return {"items": json.loads(text[bracket_start:i + 1])}
                    except json.JSONDecodeError:
                        break

    _logger.warning(f"[{agent_name}] Failed to parse JSON: {text[:200]}...")
    return None
