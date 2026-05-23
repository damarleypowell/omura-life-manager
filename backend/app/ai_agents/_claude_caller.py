"""
Shared AI caller for all Omura worker agents.

Primary: Anthropic Claude Haiku (fast, high rate limits).
Fallback: Google Gemini Flash (if Anthropic unavailable/rate-limited).
"""

from __future__ import annotations

import json
import re
import time
import traceback
from typing import Any, Optional

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger

_logger = OmuraLogger("ai_caller")

ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
GEMINI_MODEL = "gemini-2.0-flash"

# Lazy-initialized clients
_anthropic_client = None
_gemini_client = None


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None and settings.ANTHROPIC_API_KEY:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic_client


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        api_key = settings.GEMINI_FLASH_KEY or settings.GEMINI_API_KEY
        if api_key:
            from google import genai
            _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("429", "quota", "resource_exhausted", "rate_limit", "rate limit", "overloaded"))


def _call_anthropic(prompt: str, system_prompt: str, agent_name: str, temperature: float, max_tokens: int) -> Optional[str]:
    client = _get_anthropic()
    if not client:
        return None
    for attempt, delay in enumerate([0, 20, 60]):
        if delay:
            _logger.warning(f"[{agent_name}] Anthropic rate limited — retrying in {delay}s")
            time.sleep(delay)
        try:
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as exc:
            if _is_rate_limit(exc) and attempt < 2:
                continue
            _logger.error(f"[{agent_name}] Anthropic error: {exc}")
            return None


def _call_gemini(prompt: str, system_prompt: str, agent_name: str, temperature: float, max_tokens: int) -> Optional[str]:
    client = _get_gemini()
    if not client:
        return None
    from google.genai import types
    for attempt, delay in enumerate([0, 20, 60]):
        if delay:
            _logger.warning(f"[{agent_name}] Gemini rate limited — retrying in {delay}s")
            time.sleep(delay)
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            return response.text or ""
        except Exception as exc:
            if _is_rate_limit(exc) and attempt < 2:
                continue
            _logger.error(f"[{agent_name}] Gemini error: {exc}")
            return None


def call_claude(
    prompt: str,
    system_prompt: str,
    agent_name: str = "agent",
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> Optional[str]:
    """Call AI and return raw text. Tries Anthropic first, falls back to Gemini."""
    result = _call_anthropic(prompt, system_prompt, agent_name, temperature, max_tokens)
    if result is not None:
        _logger.debug(f"[{agent_name}] Anthropic call successful ({len(result)} chars)")
        return result

    _logger.warning(f"[{agent_name}] Anthropic unavailable — falling back to Gemini")
    result = _call_gemini(prompt, system_prompt, agent_name, temperature, max_tokens)
    if result is not None:
        _logger.debug(f"[{agent_name}] Gemini fallback successful ({len(result)} chars)")
    return result


def call_claude_json(
    prompt: str,
    system_prompt: str,
    agent_name: str = "agent",
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> Optional[dict]:
    """Call AI and parse response as JSON."""
    raw = call_claude(
        prompt=prompt,
        system_prompt=system_prompt,
        agent_name=agent_name,
        temperature=temperature,
        max_tokens=max_tokens,
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
