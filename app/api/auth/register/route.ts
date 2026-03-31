import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { hashPassword } from "@/lib/auth/hash";
import { createSession } from "@/lib/auth/session";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { email, password, name } = body as {
      email?: string;
      password?: string;
      name?: string;
    };

    if (!email || !password) {
      return NextResponse.json(
        { error: "Email and password are required." },
        { status: 400 },
      );
    }

    const existing = await prisma.user.findUnique({ where: { email } });
    if (existing) {
      return NextResponse.json(
        { error: "User with this email already exists." },
        { status: 400 },
      );
    }

    const hashed = await hashPassword(password);

    const user = await prisma.user.create({
      data: {
        email,
        password: hashed,
        name,
      },
    });

    const workspace = await prisma.workspace.create({
      data: {
        name: `${name ?? email}'s workspace`,
        ownerId: user.id,
        users: {
          connect: { id: user.id },
        },
      },
    });

    await createSession({ userId: user.id, workspaceId: workspace.id });

    return NextResponse.json(
      {
        user: { id: user.id, email: user.email, name: user.name },
        workspace: { id: workspace.id, name: workspace.name },
      },
      { status: 201 },
    );
  } catch (error) {
    console.error("Register error", error);
    return NextResponse.json(
      { error: "Unexpected error during registration." },
      { status: 500 },
    );
  }
}


