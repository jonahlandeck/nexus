import { redirect } from "next/navigation";

import { auth, signIn } from "@/auth";

// Auth.js kicks off the OIDC flow; Authentik (auth.landeck.pro) renders the
// real login / signup UI on its own domain. nexus builds no login form.
export default async function LoginPage() {
  const session = await auth();
  if (session) redirect("/dashboard");

  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center px-6">
      <h1 className="text-lg font-semibold">nexus</h1>
      <p className="mt-1 text-sm text-neutral-500">
        One account for every landeck.pro app.
      </p>

      <form
        className="mt-8"
        action={async () => {
          "use server";
          await signIn("authentik", { redirectTo: "/dashboard" });
        }}
      >
        <button
          type="submit"
          className="w-full rounded-md bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-700 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
        >
          Continue with landeck.pro
        </button>
      </form>
    </main>
  );
}
