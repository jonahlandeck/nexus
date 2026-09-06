"""Thin async client for an Ollama-compatible server.

Exposes two calls:
  * chat(messages, cfg)              -> plain assistant text
  * generate_json(messages, cfg, schema) -> parsed dict, with a repair retry loop

On Cloudflare Workers the only outbound HTTP that works is fetch-based, so this
uses ``httpx.AsyncClient``. ``OLLAMA_URL`` must point at a host reachable from
the edge (a localhost Ollama is not).
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from ..config import Settings, get_settings


class LLMError(RuntimeError):
    pass


async def _chat_raw(
    messages: list[dict[str, str]], cfg: Settings, fmt: Any | None = None
) -> str:
    payload: dict[str, Any] = {
        "model": cfg.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.4},
    }
    if fmt is not None:
        payload["format"] = fmt
    try:
        async with httpx.AsyncClient(
            base_url=cfg.ollama_url, timeout=httpx.Timeout(cfg.ollama_timeout)
        ) as c:
            r = await c.post("/api/chat", json=payload)
    except httpx.HTTPError as exc:  # pragma: no cover - network dependent
        raise LLMError(
            f"Could not reach the model server at {cfg.ollama_url}. "
            f"({exc})"
        ) from exc
    if r.status_code != 200:
        raise LLMError(f"Model server returned {r.status_code}: {r.text[:400]}")
    data = r.json()
    return data.get("message", {}).get("content", "")


async def chat(messages: list[dict[str, str]], cfg: Settings | None = None) -> str:
    return (await _chat_raw(messages, cfg or get_settings())).strip()


async def generate_json(
    messages: list[dict[str, str]],
    cfg: Settings | None = None,
    schema: dict[str, Any] | None = None,
    retries: int = 2,
) -> dict[str, Any]:
    """Call the model asking for JSON and parse it, repairing on failure."""
    cfg = cfg or get_settings()
    convo = list(messages)
    fmt: Any = schema if schema is not None else "json"
    last_err = ""
    for attempt in range(retries + 1):
        raw = await _chat_raw(convo, cfg, fmt=fmt)
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
