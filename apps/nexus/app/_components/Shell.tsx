import Link from "next/link";
import type { ReactNode } from "react";

import { doSignOut } from "@/lib/actions";

export function Shell({
  email,
  children,
}: {
  email?: string | null;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <header className="flex items-center justify-between">
        <Link href="/dashboard" className="text-sm font-semibold">
          nexus
        </Link>
        <div className="flex items-center gap-3 text-sm text-neutral-500">
          {email ? <span>{email}</span> : null}
          <form action={doSignOut}>
            <button
              type="submit"
              className="rounded-md px-2 py-1 hover:bg-neutral-200 dark:hover:bg-neutral-800"
            >
              Sign out
            </button>
          </form>
        </div>
      </header>
      <main className="mt-10">{children}</main>
    </div>
  );
}
