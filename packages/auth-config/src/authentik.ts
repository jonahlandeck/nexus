/**
 * Thin client for the Authentik REST API (v3), used by nexus /admin.
 *
 * Auth is a bearer token belonging to the `svc-nexus` service account, scoped
 * by the `nexus-admin-api` role to user/group read-write only (see
 * authentik/blueprints/nexus.yaml). It must NOT be the akadmin bootstrap token.
 */

export interface AuthentikGroupRef {
  pk: string;
  name: string;
}

export interface AuthentikUser {
  pk: number;
  username: string;
  name: string;
  email: string;
  is_active: boolean;
  /** Group UUIDs. */
  groups: string[];
  /** Present when the list call asks for `include_groups`. */
  groups_obj?: AuthentikGroupRef[];
}

export interface AuthentikGroup {
  pk: string;
  /** Integer PK, handy for some legacy endpoints. */
  num_pk: number;
  name: string;
  is_superuser: boolean;
  users: number[];
}

interface Paginated<T> {
  pagination: { next: number; previous: number; count: number; total_pages: number };
  results: T[];
}

export class AuthentikError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body?: unknown,
  ) {
    super(message);
    this.name = "AuthentikError";
  }
}

export class AuthentikClient {
  private readonly base: string;
  private readonly token: string;

  /** @param baseUrl e.g. https://auth.landeck.pro/api/v3 */
  constructor(baseUrl: string, token: string) {
    this.base = baseUrl.replace(/\/+$/, "");
    this.token = token;
  }

  private async req<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${this.base}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(init?.headers ?? {}),
      },
    });
    const text = await res.text();
    const body = text ? JSON.parse(text) : null;
    if (!res.ok) {
      throw new AuthentikError(
        `Authentik ${init?.method ?? "GET"} ${path} -> ${res.status}`,
        res.status,
        body,
      );
    }
    return body as T;
  }

  /** Paginate through every page of a list endpoint. */
  private async list<T>(path: string, pageSize = 100): Promise<T[]> {
    const out: T[] = [];
    const sep = path.includes("?") ? "&" : "?";
    let page = 1;
    for (;;) {
      const res = await this.req<Paginated<T>>(
        `${path}${sep}page=${page}&page_size=${pageSize}`,
      );
      out.push(...res.results);
      if (!res.pagination || page >= res.pagination.total_pages) break;
      page += 1;
    }
    return out;
  }

  listUsers(): Promise<AuthentikUser[]> {
    return this.list<AuthentikUser>("/core/users/?include_groups=true");
  }

  listGroups(): Promise<AuthentikGroup[]> {
    return this.list<AuthentikGroup>("/core/groups/");
  }

  async addUserToGroup(groupPk: string, userPk: number): Promise<void> {
    await this.req(`/core/groups/${groupPk}/add_user/`, {
      method: "POST",
      body: JSON.stringify({ pk: userPk }),
    });
  }

  async removeUserFromGroup(groupPk: string, userPk: number): Promise<void> {
    await this.req(`/core/groups/${groupPk}/remove_user/`, {
      method: "POST",
      body: JSON.stringify({ pk: userPk }),
    });
  }

  createUser(input: {
    username: string;
    name: string;
    email?: string;
    groups?: string[];
  }): Promise<AuthentikUser> {
    return this.req<AuthentikUser>("/core/users/", {
      method: "POST",
      body: JSON.stringify({
        username: input.username,
        name: input.name,
        email: input.email ?? "",
        path: "users",
        type: "internal",
        groups: input.groups ?? [],
      }),
    });
  }

  /**
   * Create an enrollment invitation. Requires an `invitation` stage wired into
   * an enrollment flow in Authentik. The usable link is
   *   `${authentikBaseUrl}/if/flow/<enrollment-flow-slug>/?itoken=<pk>`
   */
  createInvite(input: {
    name: string;
    expiresISO: string;
    groupPk?: string;
    singleUse?: boolean;
  }): Promise<{ pk: string; flow_obj?: { slug: string } }> {
    return this.req("/stages/invitation/invitations/", {
      method: "POST",
      body: JSON.stringify({
        name: input.name,
        expires: input.expiresISO,
        single_use: input.singleUse ?? true,
        fixed_data: input.groupPk ? { groups: [input.groupPk] } : {},
      }),
    });
  }
}
