//Viewer goes here to input code to join a host session

import { joinViewer } from "../store/sessionStore";

// POST /api/session/join
export async function POST(req) {
  try {
    const { sessionId, inputLang, outputLang } = await req.json();

    // check input validity
    if (!sessionId) {
      return new Response("Missing sessionId", { status: 400 });
    }

    // add viewer to the in-memory session
    const viewerId = joinViewer(sessionId, { inputLang, outputLang });

    // return viewer identifier
    return Response.json({ viewerId });
  } catch (err) {
    console.error("Error joining session:", err);
    return new Response("Failed to join session", { status: 500 });
  }
}
