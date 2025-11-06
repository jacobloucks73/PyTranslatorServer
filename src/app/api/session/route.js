import { NextResponse } from "next/server";
import { createSession } from "./store/sessionStore";

// POST /api/session
export async function POST(req) {
  try {
    // extract body fields
    const { inputLang, outputLang, isPrivate } = await req.json();

    // create session in memory
    const sessionId = createSession({ inputLang, outputLang, isPrivate });

    // optional: log for debugging
    console.log("🆕 Session created:", { sessionId, inputLang, outputLang, isPrivate });

    // return JSON response
    return NextResponse.json({ sessionId });
  } catch (err) {
    console.error("Error creating session:", err);
    return NextResponse.json({ error: "Failed to create session" }, { status: 500 });
  }
}


// create session, routes to where the session needs to go