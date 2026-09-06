"""Thin client for a local Ollama server.

Exposes two calls:
  * chat(messages)              -> plain assistant text
  * generate_json(messages, schema) -> parsed dict, with a repair retry loop
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from ..config import get_settings


class LLMError(RuntimeError):
    pass


def _client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(base_url=s.ollama_url, timeout=httpx.Timeout(s.ollama_timeout))


def _chat_raw(messages: list[dict[str, str]], fmt: Any | None = None) -> str:
    s = get_settings()
    payload: dict[str, Any] = {
        "model": s.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.4},
    }
    if fmt is not None:
        payload["format"] = fmt
    try:
        with _client() as c:
            r = c.post("/api/chat", json=payload)
    except httpx.HTTPError as exc:  # pragma: no cover - network dependent
        raise LLMError(
            f"Could not reach Ollama at {s.ollama_url}. Is `ollama serve` running "
            f"and `{s.ollama_model}` pulled?  ({exc})"
        ) from exc
    if r.status_code != 200:
        raise LLMError(f"Ollama returned {r.status_code}: {r.text[:400]}")
    data = r.json()
    return data.get("message", {}).get("content", "")


def chat(messages: list[dict[str, str]]) -> str:
    return _chat_raw(messages).strip()


def generate_json(
    messages: list[dict[str, str]],
    schema: dict[str, Any] | None = None,
    retries: int = 2,
) -> dict[str, Any]:
    """Call the model asking for JSON and parse it, repairing on failure."""
    convo = list(messages)
    fmt: Any = schema if schema is not None else "json"
    last_err = ""
    for attempt in range(retries + 1):
        raw = _chat_raw(convo, fmt=fmt)
        parsed = _try_parse(raw)
        if parsed is not None:
            return parsed
        last_err = f"attempt {attempt + 1}: could not parse JSON from: {raw[:200]!r}"
        convo = convo + [
            {"role": "assistant", "content": raw},
            {
                "role": "user",
                "content": (
                    "That was not valid JSON. Reply with ONLY a single JSON object, "
                    "no prose, no markdown fences."
                ),
            },
        ]
    raise LLMError(f"Model did not return valid JSON. {last_err}")


def _try_parse(raw: str) -> dict[str, Any] | None:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        # last resort: grab the outermost {...}
        start, end = raw.find("{"), raw.rfind("}")
        if 0 <= start < end:
            try:
                obj = json.loads(raw[start : end + 1])
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                return None
        return None
