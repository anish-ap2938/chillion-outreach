import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { verifyPassword } from "@/lib/auth/hash";
import { createSession } from "@/lib/auth/session";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { email, password } = body as {
      email?: string;
      password?: string;
    };

    if (!email || !password) {
      return NextResponse.json(
        { error: "Email and password are required." },
        { status: 400 },
      );
    }

    const user = await prisma.user.findUnique({
      where: { email },
      include: { ownedWorkspaces: true },
    });

    if (!user) {
      return NextResponse.json(
        { error: "Invalid email or password." },
        { status: 401 },
      );
    }

    const valid = await verifyPassword(password, user.password);
    if (!valid) {
      return NextResponse.json(
        { error: "Invalid email or password." },
        { status: 401 },
      );
    }

    const workspace =
      user.ownedWorkspaces[0] ??
      (await prisma.workspace.findFirst({
        where: { users: { some: { id: user.id } } },
      }));

    if (!workspace) {
      return NextResponse.json(
        { error: "No workspace associated with this user." },
        { status: 500 },
      );
    }

    await createSession({ userId: user.id, workspaceId: workspace.id });

    return NextResponse.json(
      {
        user: { id: user.id, email: user.email, name: user.name },
        workspace: { id: workspace.id, name: workspace.name },
      },
      { status: 200 },
    );
  } catch (error) {
    console.error("Login error", error);
    return NextResponse.json(
      { error: "Unexpected error during login." },
      { status: 500 },
    );
  }
}


