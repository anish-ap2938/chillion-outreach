"use server";

import { cookies } from "next/headers";
import { prisma } from "@/lib/db";
import { randomBytes } from "crypto";

const SESSION_COOKIE_NAME = "agency_ai_session";
const SESSION_TTL_DAYS = 7;

function getExpiryDate() {
  const date = new Date();
  date.setDate(date.getDate() + SESSION_TTL_DAYS);
  return date;
}

export async function createSession(params: {
  userId: string;
  workspaceId: string;
}) {
  const token = randomBytes(32).toString("hex");
  const expiresAt = getExpiryDate();

  await prisma.session.create({
    data: {
      token,
      userId: params.userId,
      workspaceId: params.workspaceId,
      expiresAt,
    },
  });

  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    expires: expiresAt,
  });
}

export async function destroySession() {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (!token) return;

  await prisma.session.deleteMany({ where: { token } });
  cookieStore.set(SESSION_COOKIE_NAME, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    expires: new Date(0),
  });
}

export async function getCurrentSession() {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;

  const session = await prisma.session.findFirst({
    where: {
      token,
      expiresAt: { gt: new Date() },
    },
    include: {
      user: true,
      workspace: true,
    },
  });
  return session;
}


