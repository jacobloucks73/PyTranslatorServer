//lets a viewer join a existing session

// /app/api/session/join/route.js
import { joinViewer } from "../store/sessionStore";

export async function POST(req) {
  const { sessionId, inputLang, outputLang } = await req.json();
  const viewerId = joinViewer(sessionId, { inputLang, outputLang });
  return Response.json({ viewerId });
}
