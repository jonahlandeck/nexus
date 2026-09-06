-- Meat And Potatoes - Cloudflare D1 schema.
-- Apply locally:  npx wrangler d1 migrations apply meat-and-potatoes --local
-- Apply remote:   npx wrangler d1 migrations apply meat-and-potatoes --remote
--
-- Notes vs. the old SQLAlchemy/SQLite schema:
--   * booleans are stored as INTEGER 0/1
--   * timestamps are TEXT ISO-8601 in UTC, written by the app (D1 has no
--     server-side func.now() default that the app relied on)

CREATE TABLE IF NOT EXISTS profiles (
    id         INTEGER PRIMARY KEY,        -- always 1
    data       TEXT NOT NULL DEFAULT '{}', -- JSON
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS intake_sessions (
    id         TEXT PRIMARY KEY,
    transcript TEXT NOT NULL DEFAULT '[]', -- JSON  [{role, content}]
    complete   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plans (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt           TEXT NOT NULL DEFAULT '',
    profile_snapshot TEXT NOT NULL DEFAULT '{}', -- JSON
    notes            TEXT NOT NULL DEFAULT '',
    days             INTEGER NOT NULL DEFAULT 7,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id         INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    day             TEXT NOT NULL,
    day_index       INTEGER NOT NULL DEFAULT 0,
    slot            TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    servings        INTEGER NOT NULL DEFAULT 1,
    approx_calories INTEGER
);

CREATE TABLE IF NOT EXISTS ingredients (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    meal_id  INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
    name     TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 0,
    unit     TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    staple   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pantry_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS product_matches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id         INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    line_key        TEXT NOT NULL,
    query           TEXT NOT NULL,
    display_name    TEXT NOT NULL,
    quantity_needed REAL NOT NULL DEFAULT 1,
    item_id         TEXT,
    product_name    TEXT,
    price           REAL,
    in_stock        INTEGER NOT NULL DEFAULT 1,
    image_url       TEXT,
    product_url     TEXT,
    seller          TEXT,
    cart_quantity   INTEGER NOT NULL DEFAULT 1,
    manual          INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_product_matches_plan_id  ON product_matches(plan_id);
CREATE INDEX IF NOT EXISTS ix_product_matches_line_key ON product_matches(line_key);

CREATE TABLE IF NOT EXISTS search_cache (
    cache_key     TEXT PRIMARY KEY,
    query         TEXT NOT NULL,
    response_json TEXT NOT NULL,
    fetched_at    TEXT NOT NULL
);
