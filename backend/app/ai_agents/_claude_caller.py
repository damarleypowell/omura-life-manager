"""
Shared Gemini API caller for all Omura AI agents.

Provides a reusable function that sends prompts to the Google Gemini API
and parses JSON-structured responses. Uses Gemini Flash for worker agents.
Falls back gracefully on failure.
"""

from __future__ import annotations

import json
import re
import traceback
from typing import Any, Optional

from google import genai
from google.genai import types

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger

_logger = OmuraLogger("gemini_caller")

# Shared client instance — created lazily
_client: Optional[genai.Client] = None

# Flash for all worker agents — fast and free-tier friendly
MODEL = "gemini-2.5-flash"


def _get_client() -> genai.Client:
    """Return a shared Gemini Flash client instance."""
    global _client
    if _client is None:
        api_key = settings.GEMINI_FLASH_KEY or settings.GEMINI_API_KEY
        _client = genai.Client(api_key=api_key)
    return _client


def call_claude(
    prompt: str,
    system_prompt: str,
    agent_name: str = "agent",
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> Optional[str]:
    """Call Gemini Flash API and return the raw text response.

    Args:
        prompt: The user message to send.
        system_prompt: The system prompt defining agent behavior.
        agent_name: Name of the calling agent (for logging).
        temperature: Sampling temperature (lower = more deterministic).
        max_tokens: Maximum tokens in the response.

    Returns:
        The text content of the response, or None on failure.
    """
    if not (settings.GEMINI_FLASH_KEY or settings.GEMINI_API_KEY):
        _logger.warning(f"[{agent_name}] No GEMINI_FLASH_KEY or GEMINI_API_KEY configured, skipping API call")
        return None

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )

        result = response.text or ""
        _logger.debug(f"[{agent_name}] Gemini API call successful, response length: {len(result)}")
        return result

    except Exception as exc:
        _logger.error(f"[{agent_name}] Gemini API error: {traceback.format_exc()}")
        return None


def call_claude_json(
    prompt: str,
    system_prompt: str,
    agent_name: str = "agent",
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> Optional[dict]:
    """Call Gemini API and parse the response as JSON.

    The system prompt should instruct the model to respond with valid JSON.
    This function attempts to extract JSON from the response, handling
    cases where the model wraps JSON in markdown code blocks.

    Args:
        prompt: The user message to send.
        system_prompt: The system prompt (should request JSON output).
        agent_name: Name of the calling agent (for logging).
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in the response.

    Returns:
        A parsed dict from the JSON response, or None on failure.
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
    """Extract and parse JSON from a Gemini response.

    Handles common response formats:
    - Pure JSON
    - JSON wrapped in ```json ... ``` code blocks
    - JSON with leading/trailing text

    Args:
        text: The raw text response.
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
                        return {"items": parsed}
                    except json.JSONDecodeError:
                        break

    _logger.warning(f"[{agent_name}] Failed to parse JSON from response: {text[:200]}...")
    return None
