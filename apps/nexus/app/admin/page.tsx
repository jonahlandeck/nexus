import { notFound } from "next/navigation";

import { auth } from "@/auth";
import { getEnv } from "@/lib/cf";
import { listRecentAudit } from "@/lib/audit";
import { AuthentikClient, isAdmin } from "@nexus/auth";

import { Shell } from "../_components/Shell";
import { setMembership } from "./actions";

// Always fresh: reflects Authentik state and the audit log.
export const dynamic = "force-dynamic";

export default async function AdminPage() {
  const session = await auth();
  if (!isAdmin(session)) notFound();

  const env = getEnv();
  const ak = new AuthentikClient(
    env.AUTHENTIK_API_URL,
    await env.AUTHENTIK_API_TOKEN.get(),
  );

  const [users, groups, audit] = await Promise.all([
    ak.listUsers(),
    ak.listGroups(),
    listRecentAudit(env.DB, 25),
  ]);

  // Never surface superuser groups as toggles from here.
  const managed = groups
    .filter((g) => !g.is_superuser)
    .sort((a, b) => a.name.localeCompare(b.name));

  return (
    <Shell email={session!.user?.email}>
      <h1 className="text-base font-semibold">Admin</h1>

      <section className="mt-6">
        <h2 className="text-sm font-medium text-neutral-500">
          Users &amp; group access
        </h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-neutral-200 text-left dark:border-neutral-800">
                <th className="py-2 pr-4 font-medium">User</th>
                {managed.map((g) => (
                  <th key={g.pk} className="px-3 py-2 font-medium">
                    {g.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr
                  key={u.pk}
                  className="border-b border-neutral-100 dark:border-neutral-900"
                >
                  <td className="py-2 pr-4">
                    <span className="font-medium">{u.name || u.username}</span>
                    <span className="block text-xs text-neutral-500">
                      {u.email || u.username}
                      {u.is_active ? "" : " · inactive"}
                    </span>
                  </td>
                  {managed.map((g) => {
                    const isMember = u.groups.includes(g.pk);
                    return (
                      <td key={g.pk} className="px-3 py-2">
                        <form action={setMembership}>
                          <input
                            type="hidden"
                            name="op"
                            value={isMember ? "remove" : "add"}
                          />
                          <input type="hidden" name="groupPk" value={g.pk} />
                          <input
                            type="hidden"
                            name="groupName"
                            value={g.name}
                          />
                          <input type="hidden" name="userPk" value={u.pk} />
                          <button
                            type="submit"
                            className={
                              isMember
                                ? "rounded-md bg-neutral-900 px-2 py-1 text-xs text-white dark:bg-white dark:text-neutral-900"
                                : "rounded-md border border-neutral-300 px-2 py-1 text-xs text-neutral-500 dark:border-neutral-700"
                            }
                          >
                            {isMember ? "member" : "add"}
                          </button>
                        </form>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-medium text-neutral-500">Recent activity</h2>
        <ul className="mt-3 space-y-1 text-sm">
          {audit.length === 0 ? (
            <li className="text-neutral-500">No admin actions recorded yet.</li>
          ) : (
            audit.map((row) => (
              <li key={row.id} className="text-neutral-600 dark:text-neutral-400">
                <span className="tabular-nums text-neutral-400">
                  {row.created_at}
                </span>{" "}
                — <span className="font-medium">{row.action}</span> {row.target}{" "}
                <span className="text-neutral-400">by {row.actor_sub}</span>
              </li>
            ))
          )}
        </ul>
      </section>
    </Shell>
  );
}
