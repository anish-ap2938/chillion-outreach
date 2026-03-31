import { NextResponse } from "next/server";
import { destroySession } from "@/lib/auth/session";

export async function POST() {
  try {
    await destroySession();
    return NextResponse.json({ ok: true }, { status: 200 });
  } catch (error) {
    console.error("Logout error", error);
    return NextResponse.json(
      { error: "Unexpected error during logout." },
      { status: 500 },
    );
  }
}


