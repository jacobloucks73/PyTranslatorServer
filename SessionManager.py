# session_manager.py

from typing import Dict, Set
import asyncio
import json

class SessionManager:
    def __init__(self):
        # session_id -> set of active WebSocket connections
        self.active_sessions: Dict[str, Set] = {}
        # lock to avoid race conditions
        self.lock = asyncio.Lock()

        session_manager = SessionManager()

    async def register(self, session_id: str, websocket):
        async with self.lock:
            if session_id not in self.active_sessions:
                self.active_sessions[session_id] = set()
            self.active_sessions[session_id].add(websocket)

    async def unregister(self, session_id: str, websocket):
        async with self.lock:
            if session_id in self.active_sessions:
                self.active_sessions[session_id].discard(websocket)
                if not self.active_sessions[session_id]:
                    del self.active_sessions[session_id]

    async def send_to_frontend(self, session_id: str, message: dict):
        """Called by translator or punctuator to push out messages."""
        async with self.lock:
            conns = self.active_sessions.get(session_id, set()).copy()

        if not conns:
            return  # no frontend connected

        dead = []
        data = json.dumps(message)

        for ws in conns:
            try:
                await ws.send_text(data)
            except:
                dead.append(ws)

        # cleanup dead sockets
        async with self.lock:
            for ws in dead:
                self.active_sessions[session_id].discard(ws)
