"""Thin async wrapper around a Cloudflare D1 binding + FastAPI dependencies.

The ASGI adapter (workers.asgi) puts the Worker ``env`` object on the ASGI
scope, so every request handler can reach the bindings via ``request.scope``.

D1's JS API::

    await env.DB.prepare(sql).bind(*params).all()    -> {results: [...], meta}
    await env.DB.prepare(sql).bind(*params).first()  -> row | None
    await env.DB.prepare(sql).bind(*params).run()    -> {meta: {last_row_id, changes}}
"""
from __future__ import annotations

from typing import Any

from fastapi import Request

from .config import Settings, get_settings


def _to_py(value: Any) -> Any:
    """Convert a JS proxy (object/array) to plain Python, tolerate real Python."""
    if value is None:
        return None
    to_py = getattr(value, "to_py", None)
    if callable(to_py):
        return to_py()
    return value


def _bind_value(v: Any) -> Any:
    if isinstance(v, bool):
        return 1 if v else 0
    return v


class D1:
    """Awaitable helpers over a single D1 binding."""

    def __init__(self, binding: Any) -> None:
        self._db = binding

    def _stmt(self, sql: str, params: tuple[Any, ...]):
        stmt = self._db.prepare(sql)
        if params:
            stmt = stmt.bind(*[_bind_value(p) for p in params])
        return stmt

    async def all(self, sql: str, *params: Any) -> list[dict[str, Any]]:
        res = await self._stmt(sql, params).all()
        results = getattr(res, "results", None)
        if results is None:
            return []
        rows = _to_py(results)
        return [dict(_to_py(r)) for r in rows]

    async def first(self, sql: str, *params: Any) -> dict[str, Any] | None:
        res = await self._stmt(sql, params).first()
        res = _to_py(res)
        return dict(res) if res is not None else None

    async def value(self, sql: str, *params: Any) -> Any:
        """First column of the first row (for COUNT/MAX style queries)."""
        row = await self.first(sql, *params)
        if not row:
            return None
        return next(iter(row.values()))

    async def run(self, sql: str, *params: Any) -> dict[str, Any]:
        res = await self._stmt(sql, params).run()
        meta = _to_py(getattr(res, "meta", None))
        return dict(meta) if meta else {}

    async def insert(self, sql: str, *params: Any) -> int:
        """Run an INSERT and return the new rowid."""
        meta = await self.run(sql, *params)
        for key in ("last_row_id", "lastRowId", "last_insert_rowid"):
            if meta.get(key):
                return int(meta[key])
        return 0


# --- FastAPI dependencies --------------------------------------------------


def get_env(request: Request) -> Any:
    return request.scope.get("env")


def get_db(request: Request) -> D1:
    env = request.scope.get("env")
    binding = getattr(env, "DB", None) if env is not None else None
    if binding is None:
        raise RuntimeError(
            "D1 binding 'DB' is missing. Add a [[d1_databases]] entry to "
            "wrangler.jsonc (binding = \"DB\")."
        )
    return D1(binding)


def get_config(request: Request) -> Settings:
    return get_settings(request.scope.get("env"))
