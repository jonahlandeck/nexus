-- Auth.js Cloudflare D1 adapter schema.
--
-- COPIED VERBATIM from @auth/d1-adapter's migrations.ts (upstream:
-- packages/adapter-d1/src/migrations.ts in nextauthjs/next-auth). Do NOT
-- hand-edit column names or types — a wrong type here fails silently
-- (sign-ins break, or partially work). After `pnpm install`, re-diff this
-- against node_modules/@auth/d1-adapter and use whatever it actually ships;
-- `up(env.DB)` from the adapter is the authoritative fallback.
--
-- With session.strategy = "jwt" (see @nexus/auth), "sessions" and
-- "verification_tokens" are created but unused; kept for future email flows.
--
-- Apply:  npx wrangler d1 migrations apply nexus --local   (dev)
--         npx wrangler d1 migrations apply nexus --remote  (prod)

CREATE TABLE IF NOT EXISTS "accounts" (
    "id" text NOT NULL,
    "userId" text NOT NULL DEFAULT NULL,
    "type" text NOT NULL DEFAULT NULL,
    "provider" text NOT NULL DEFAULT NULL,
    "providerAccountId" text NOT NULL DEFAULT NULL,
    "refresh_token" text DEFAULT NULL,
    "access_token" text DEFAULT NULL,
    "expires_at" number DEFAULT NULL,
    "token_type" text DEFAULT NULL,
    "scope" text DEFAULT NULL,
    "id_token" text DEFAULT NULL,
    "session_state" text DEFAULT NULL,
    "oauth_token_secret" text DEFAULT NULL,
    "oauth_token" text DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS "sessions" (
    "id" text NOT NULL,
    "sessionToken" text NOT NULL,
    "userId" text NOT NULL DEFAULT NULL,
    "expires" datetime NOT NULL DEFAULT NULL,
    PRIMARY KEY (sessionToken)
);

CREATE TABLE IF NOT EXISTS "users" (
    "id" text NOT NULL DEFAULT '',
    "name" text DEFAULT NULL,
    "email" text DEFAULT NULL,
    "emailVerified" datetime DEFAULT NULL,
    "image" text DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS "verification_tokens" (
    "identifier" text NOT NULL,
    "token" text NOT NULL DEFAULT NULL,
    "expires" datetime NOT NULL DEFAULT NULL,
    PRIMARY KEY (token)
);
