import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    /** Authentik group names, from the `groups` claim (see config.ts jwt callback). */
    groups: string[];
    user: {
      /** Stable Authentik subject. Key per-app data by this, never by email. */
      sub: string;
    } & DefaultSession["user"];
  }
}

// The JWT interface in Auth.js v5 already extends Record<string, unknown>, so
// `token.groups` needs no module augmentation (augmenting "next-auth/jwt" also
// trips TS2664 under pnpm's nested layout). config.ts reads it defensively.

export {};
