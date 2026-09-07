-- nexus-local tables (not part of the Auth.js adapter).

-- Append-only record of every admin action taken in /admin. This is the whole
-- reason shared admin logins are forbidden: actor_sub is the acting admin's
-- Authentik subject, so actions are attributable to a named person.
CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_sub  TEXT NOT NULL,
    action     TEXT NOT NULL,              -- e.g. "group.add", "group.remove"
    target     TEXT NOT NULL,              -- e.g. "user:42"
    detail     TEXT NOT NULL DEFAULT '{}', -- JSON
    created_at TEXT NOT NULL               -- ISO-8601 UTC, written by the app
);
CREATE INDEX IF NOT EXISTS ix_audit_log_created_at ON audit_log(created_at DESC);
