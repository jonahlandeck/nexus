import Link from "next/link";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { accessibleApps } from "@nexus/auth";

import { Shell } from "../_components/Shell";

export default async function DashboardPage() {
  const session = await auth();
  if (!session) redirect("/login");

  const apps = accessibleApps(session);

  return (
    <Shell email={session.user?.email}>
      <h1 className="text-base font-semibold">Your apps</h1>
      <ul className="mt-4 grid gap-3 sm:grid-cols-2">
        {apps.map((app) => {
          const inner = (
            <>
              <span className="text-sm font-medium">{app.name}</span>
              <span className="mt-1 block text-sm text-neutral-500">
                {app.description}
              </span>
            </>
          );
          const className =
            "block rounded-lg border border-neutral-200 p-4 hover:border-neutral-400 dark:border-neutral-800 dark:hover:border-neutral-600";
          return (
            <li key={app.slug}>
              {app.external ? (
                <a
                  href={app.url}
                  target="_blank"
                  rel="noreferrer"
                  className={className}
                >
                  {inner}
                </a>
              ) : (
                <Link href={app.url} className={className}>
                  {inner}
                </Link>
              )}
            </li>
          );
        })}
      </ul>
    </Shell>
  );
}
