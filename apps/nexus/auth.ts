import { getCloudflareContext } from "@opennextjs/cloudflare";
import { buildAuthConfig, type NexusAuthEnv } from "@nexus/auth";
import NextAuth from "next-auth";

// Async factory: Secrets Store bindings resolve with `await env.X.get()`, and
// `getCloudflareContext({ async: true })` gives us `env` outside a request too
// (module eval, middleware).
export const { handlers, auth, signIn, signOut } = NextAuth(async () => {
  const { env } = await getCloudflareContext({ async: true });
  // CloudflareEnv (workers-types) is structurally a superset of NexusAuthEnv;
  // the cast just crosses the generated-vs-hand-written type boundary.
  return buildAuthConfig({ env: env as unknown as NexusAuthEnv });
});
