import type { Session } from "next-auth";

import { GROUPS, hasGroup } from "./groups";

export interface AppEntry {
  slug: string;
  name: string;
  description: string;
  /** Absolute URL for external apps, or a nexus-relative path (starts with "/"). */
  url: string;
  /** null = visible to any signed-in user. Otherwise an Authentik group name. */
  requiredGroup: string | null;
  /** true = leaves nexus (open in a new tab / full navigation). */
  external?: boolean;
}

/**
 * The launcher registry. "Public vs restricted" for the *app itself* is enforced
 * in Authentik via policy bindings; this list only controls what tiles nexus
 * shows on /dashboard.
 */
export const APP_REGISTRY: AppEntry[] = [
  {
    slug: "meat-and-potatoes",
    name: "Meat & Potatoes",
    description:
      "Turn a week of dinners into a single Walmart grocery cart.",
    url: "https://landeck.pro/apps/meat-and-potatoes",
    requiredGroup: null,
    external: true,
  },
  {
    slug: "admin",
    name: "Admin console",
    description: "Manage users, groups, and per-app access.",
    url: "/admin",
    requiredGroup: GROUPS.ADMINS,
  },
];

export function accessibleApps(
  session: Session | null | undefined,
): AppEntry[] {
  return APP_REGISTRY.filter(
    (a) => a.requiredGroup === null || hasGroup(session, a.requiredGroup),
  );
}
