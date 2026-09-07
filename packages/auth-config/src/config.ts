import { D1Adapter } from "@auth/d1-adapter";
import type { NextAuthConfig } from "next-auth";
import Authentik from "next-auth/providers/authentik";

import type { NexusAuthEnv } from "./env";

/**
 * Build the Auth.js config for a landeck.pro relying-party app.
 *
 * Session strategy is JWT: the D1 adapter still persists users/accounts, but no
 * D1 read happens per request, `middleware.ts` stays edge-safe, and the
 * Authentik `groups` claim rides in the token. The adapter's `sessions` /
 * `verification_tokens` tables exist for future email flows but are unused here.
 *
 * `buildAuthConfig` is async because Secrets Store bindings resolve with
 * `await env.X.get()`. Call it from an async NextAuth factory:
 *
 *   export const { handlers, auth, signIn, signOut } = NextAuth(async () => {
 *     const { env } = await getCloudflareContext({ async: true });
 *     return buildAuthConfig({ env });
 *   });
 */
export async function buildAuthConfig(opts: {
  env: NexusAuthEnv;
}): Promise<NextAuthConfig> {
  const { env } = opts;

  const [authSecret, clientSecret] = await Promise.all([
    env.AUTH_SECRET.get(),
    env.AUTHENTIK_CLIENT_SECRET.get(),
  ]);

  return {
    secret: authSecret,
    trustHost: true,
    session: { strategy: "jwt" },
    adapter: D1Adapter(env.DB),
    providers: [
      Authentik({
        clientId: env.AUTHENTIK_CLIENT_ID,
        clientSecret,
        issuer: env.AUTHENTIK_ISSUER,
      }),
    ],
    callbacks: {
      // `profile` is only present on the sign-in pass. Copy the stable subject
      // and the groups claim onto the token so RSCs/middleware can read them
      // without a network call.
      jwt({ token, profile }) {
        if (profile) {
          if (typeof profile.sub === "string") token.sub = profile.sub;
          const raw = (profile as Record<string, unknown>).groups;
          token.groups = Array.isArray(raw) ? (raw as string[]) : [];
        }
        return token;
      },
      session({ session, token }) {
        if (session.user) {
          session.user.sub = typeof token.sub === "string" ? token.sub : "";
        }
        session.groups = Array.isArray(token.groups)
          ? (token.groups as string[])
          : [];
        return session;
      },
    },
  };
}
