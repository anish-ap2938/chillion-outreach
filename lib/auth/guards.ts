"use server";

import { redirect } from "next/navigation";
import { getCurrentSession } from "@/lib/auth/session";

export async function requireSession() {
  const session = await getCurrentSession();
  if (!session) {
    redirect("/login");
  }
  return session;
}

export async function getOptionalSession() {
  return getCurrentSession();
}


