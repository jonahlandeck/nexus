"use server";

import { revalidatePath } from "next/cache";

import { auth } from "@/auth";
import { getEnv } from "@/lib/cf";
import { writeAudit } from "@/lib/audit";
import { AuthentikClient, isAdmin } from "@nexus/auth";

async function adminClient() {
  const env = getEnv();
  const ak = new AuthentikClient(
    env.AUTHENTIK_API_URL,
    await env.AUTHENTIK_API_TOKEN.get(),
  );
  return { env, ak };
}

/** Add or remove one user from one group. Records an audit_log row either way. */
export async function setMembership(formData: FormData): Promise<void> {
  const session = await auth();
  if (!isAdmin(session)) throw new Error("forbidden");

  const op = String(formData.get("op"));
  const groupPk = String(formData.get("groupPk"));
  const groupName = String(formData.get("groupName") ?? "");
  const userPk = Number(formData.get("userPk"));

  if (
    !groupPk ||
    !Number.isFinite(userPk) ||
    (op !== "add" && op !== "remove")
  ) {
    throw new Error("bad request");
  }

  const { env, ak } = await adminClient();
  if (op === "add") await ak.addUserToGroup(groupPk, userPk);
  else await ak.removeUserFromGroup(groupPk, userPk);

  await writeAudit(env.DB, {
    actorSub: session!.user.sub,
    action: `group.${op}`,
    target: `user:${userPk}`,
    detail: { groupPk, groupName },
  });

  revalidatePath("/admin");
}
