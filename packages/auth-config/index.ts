// @nexus/auth — shared identity glue for landeck.pro apps.
//
// Consumed as TypeScript source (no build step): every app that uses this
// package must list "@nexus/auth" in next.config `transpilePackages`.
import "./src/types";

export { buildAuthConfig } from "./src/config";
export type { NexusAuthEnv, SecretValue } from "./src/env";
export {
  GROUPS,
  sessionGroups,
  hasGroup,
  isAdmin,
} from "./src/groups";
export type { GroupName } from "./src/groups";
export { APP_REGISTRY, accessibleApps } from "./src/apps";
export type { AppEntry } from "./src/apps";
export { AuthentikClient, AuthentikError } from "./src/authentik";
export type { AuthentikUser, AuthentikGroup } from "./src/authentik";
