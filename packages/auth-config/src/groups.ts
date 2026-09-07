import type { Session } from "next-auth";

/**
 * Authentik groups nexus knows about by name. The `groups` claim in the token
 * is a list of group *names* (see the `groups` scope mapping in
 * authentik/blueprints/nexus.yaml).
 */
export const GROUPS = {
  ADMINS: "admins",
  BETA: "beta-testers",
} as const;

export type GroupName = (typeof GROUPS)[keyof typeof GROUPS] | (string & {});

export function sessionGroups(session: Session | null | undefined): string[] {
  if (!session) return [];
  const raw = (session as { groups?: unknown }).groups;
  return Array.isArray(raw) ? (raw as string[]) : [];
}

export function hasGroup(
  session: Session | null | undefined,
  name: GroupName,
): boolean {
  return sessionGroups(session).includes(name);
}

/** Gate for /admin. Membership check on a named account — never a shared login. */
export function isAdmin(session: Session | null | undefined): boolean {
  return hasGroup(session, GROUPS.ADMINS);
}
