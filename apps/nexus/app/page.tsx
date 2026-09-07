import { redirect } from "next/navigation";

import { auth } from "@/auth";

// No homepage content: bounce to /dashboard or /login.
export default async function Home() {
  const session = await auth();
  redirect(session ? "/dashboard" : "/login");
}
