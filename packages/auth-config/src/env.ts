import type { D1Database } from "@cloudflare/workers-types";

/**
 * A Cloudflare Secrets Store binding. Values are fetched asynchronously:
 *   const key = await env.AUTHENTIK_API_TOKEN.get();
 */
export interface SecretValue {
  get(): Promise<string>;
}

/**
 * The subset of a nexus-style Worker `env` that `buildAuthConfig` needs.
 * Secrets come from Cloudflare Secrets Store (`secrets_store_secrets` bindings);
 * the plain strings are non-secret `vars`.
 */
export interface NexusAuthEnv {
  /** D1 database for the Auth.js adapter (users/accounts tables). */
  DB: D1Database;

  // --- Secrets Store bindings ---
  AUTH_SECRET: SecretValue;
  AUTHENTIK_CLIENT_SECRET: SecretValue;
  /** Scoped service-account token (svc-nexus). NEVER the akadmin bootstrap token. */
  AUTHENTIK_API_TOKEN: SecretValue;

  // --- non-secret vars ---
  AUTHENTIK_CLIENT_ID: string;
  /** e.g. https://auth.landeck.pro/application/o/nexus/ */
  AUTHENTIK_ISSUER: string;
  /** e.g. https://auth.landeck.pro/api/v3 */
  AUTHENTIK_API_URL: string;
  AUTH_URL?: string;
}
