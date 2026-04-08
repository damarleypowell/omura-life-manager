"""
Shared Claude API caller for all Omura AI agents.

Provides a reusable function that sends prompts to the Anthropic Claude API
and parses JSON-structured responses. Falls back to mock data on failure.
"""

from __future__ import annotations

import json
import traceback
from typing import Any, Optional

import anthropic

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger

_logger = OmuraLogger("claude_caller")

# Shared client instance — created lazily
_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    """Return a shared Anthropic client instance."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


# Haiku for specialized agents — 20x cheaper, fast enough for triage/scoring/summarization
# Supervisor uses Sonnet separately (see supervisor_ai.py)
MODEL = "claude-haiku-4-5-20251001"


def call_claude(
    prompt: str,
    system_prompt: str,
    agent_name: str = "agent",
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> Optional[str]:
    """Call Claude API and return the raw text response.

    Args:
        prompt: The user message to send.
        system_prompt: The system prompt defining agent behavior.
        agent_name: Name of the calling agent (for logging).
        temperature: Sampling temperature (lower = more deterministic).
        max_tokens: Maximum tokens in the response.

    Returns:
        The text content of Claude's response, or None on failure.
    """
    if not settings.ANTHROPIC_API_KEY:
        _logger.warning(f"[{agent_name}] No ANTHROPIC_API_KEY configured, skipping API call")
        return None

    try:
        client = _get_client()
        response = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)

        result = "\n".join(text_parts)
        _logger.debug(f"[{agent_name}] Claude API call successful, response length: {len(result)}")
        return result

    except anthropic.APIConnectionError as exc:
        _logger.error(f"[{agent_name}] API connection error: {exc}")
        return None
    except anthropic.RateLimitError as exc:
        _logger.error(f"[{agent_name}] Rate limit error: {exc}")
        return None
    except anthropic.APIStatusError as exc:
        _logger.error(f"[{agent_name}] API status error {exc.status_code}: {exc}")
        return None
    except Exception as exc:
        _logger.error(f"[{agent_name}] Unexpected error calling Claude: {traceback.format_exc()}")
        return None


def call_claude_json(
    prompt: str,
    system_prompt: str,
    agent_name: str = "agent",
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> Optional[dict]:
    """Call Claude API and parse the response as JSON.

    The system prompt should instruct Claude to respond with valid JSON.
    This function attempts to extract JSON from the response, handling
    cases where Claude wraps JSON in markdown code blocks.

    Args:
        prompt: The user message to send.
        system_prompt: The system prompt (should request JSON output).
        agent_name: Name of the calling agent (for logging).
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in the response.

    Returns:
        A parsed dict from Claude's JSON response, or None on failure.
    """
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
    """Extract and parse JSON from a Claude response.

    Handles common response formats:
    - Pure JSON
    - JSON wrapped in ```json ... ``` code blocks
    - JSON with leading/trailing text

    Args:
        text: The raw text response from Claude.
        agent_name: For logging purposes.

    Returns:
        Parsed dict or None if parsing fails.
    """
    if not text:
        return None

    text = text.strip()

    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code blocks
    if "```" in text:
        # Find content between ```json and ``` or ``` and ```
        import re
        pattern = r'```(?:json)?\s*\n?(.*?)\n?\s*```'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

    # Try finding the first { ... } or [ ... ] block
    brace_start = text.find('{')
    bracket_start = text.find('[')

    if brace_start >= 0:
        # Find matching closing brace
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
                        parsed = json.loads(text[bracket_start:i + 1])
                        # Wrap list in a dict for consistency
                        return {"items": parsed}
                    except json.JSONDecodeError:
                        break

    _logger.warning(f"[{agent_name}] Failed to parse JSON from Claude response: {text[:200]}...")
    return None
