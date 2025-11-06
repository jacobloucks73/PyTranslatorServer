// logic for memory storage and backend database stuffs

// sessions.js (or sessionStore.js)
const sessions = {};  // top-level, persisted in-memory for the running process

function createSession({ inputLang, outputLang, isPrivate }) {
  const sessionId = Math.random().toString(36).substring(2, 8);
  sessions[sessionId] = {
    host: { inputLang, outputLang, isPrivate },
    viewers: {},
  };
  return sessionId;
}

function joinViewer(sessionId, { inputLang, outputLang }) {
  if (!sessions[sessionId]) throw new Error("Session not found");
  const viewerId = Math.random().toString(36).substring(2, 8);
  sessions[sessionId].viewers[viewerId] = { inputLang, outputLang };
  return viewerId;
}

function getSession(sessionId) {
  return sessions[sessionId];
}

function removeSession(sessionId) {
  delete sessions[sessionId];
}

// Export the API:
module.exports = { createSession, joinViewer, getSession, removeSession };
