"""Shared test fixtures.

Persistence is Cloudflare D1 in production; tests run the same SQL against an
in-memory ``sqlite3`` connection (identical dialect) through a small shim that
mirrors ``app.d1.D1``.
"""
import os
import pathlib
import sqlite3

import pytest

os.environ.setdefault("MAP_PROVIDER", "mock")
os.environ.setdefault("SCRAPERAPI_KEY", "test-key")

_MIGRATION = (
    pathlib.Path(__file__).resolve().parents[4] / "migrations" / "0001_init.sql"
).read_text()


class FakeD1:
    """sqlite3-backed stand-in for app.d1.D1 (same async surface)."""

    def __init__(self, con: sqlite3.Connection) -> None:
        self.con = con

    def _run(self, sql, params):
        return self.con.execute(sql, params)

    async def all(self, sql, *params):
        cur = self._run(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    async def first(self, sql, *params):
        cur = self._run(sql, params)
        row = cur.fetchone()
        if row is None:
            return None
        return dict(zip([c[0] for c in cur.description], row))

    async def value(self, sql, *params):
        row = await self.first(sql, *params)
        return next(iter(row.values())) if row else None

    async def run(self, sql, *params):
        cur = self._run(sql, params)
        self.con.commit()
        return {"last_row_id": cur.lastrowid, "changes": cur.rowcount}

    async def insert(self, sql, *params):
        return (await self.run(sql, *params))["last_row_id"]


@pytest.fixture
def d1() -> FakeD1:
    con = sqlite3.connect(":memory:")
    con.executescript(_MIGRATION)
    try:
        yield FakeD1(con)
    finally:
        con.close()
