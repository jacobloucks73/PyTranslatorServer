import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from DBStuffs.db import (
    SessionLocal, update_english, update_translation,
    update_punctuated, init_db, update_host_prefs, update_translation_target
)
from analyticTools.timelog import time_block

SESSION_LOCKS = {}
BUFFER_STORE = {}
IS_PUNCTUATING = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    print(" Shutting down gracefully...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections.setdefault(session_id, []).append(websocket)
        print(f" Connected to session {session_id}")

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            try: self.active_connections[session_id].remove(websocket)
            except ValueError: pass
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        print(f" Disconnected from session {session_id}")

    async def broadcast(self, session_id: str, message: dict):
        for connection in list(self.active_connections.get(session_id, [])):
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f" Send failed for {session_id}: {e}")
                self.disconnect(connection, session_id)

manager = ConnectionManager()

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    db = SessionLocal()
    global IS_PUNCTUATING # make session specific

    try:
        await manager.connect(websocket, session_id)

        while True:
            # --- receive message ---
            with time_block(session_id, "websocket_endpoint", "receive"):
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                source = msg.get("source")
                payload = msg.get("payload", {})

            # --- CLIENT SPEECH ---
            if source == "client":
                with time_block(session_id, "client", "update_english"):
                    english_text = payload.get("english", "")
                    if IS_PUNCTUATING: # make session specific
                        BUFFER_STORE[session_id] = BUFFER_STORE.get(session_id, "") + " " + english_text # WTF does this even do
                    else:
                        update_english(db, session_id, english_text)
                await manager.broadcast(session_id, msg)

            # --- TRANSLATION UPDATE ---
            elif source == "translate":
                with time_block(session_id, "translate", "update_translation"):
                    update_translation(
                        db, session_id,
                        msg["payload"].get("lang", "es"),
                        msg["payload"].get("translated", "")
                    )
                await manager.broadcast(session_id, msg)

            # --- PUNCTUATE UPDATE ---
            elif source == "punctuate":
                IS_PUNCTUATING = False # make session specific
                with time_block(session_id, "punctuate", "update_punctuated"):
                    punctuated_text = msg["payload"].get("english_punctuated", "")
                    await update_punctuated(db, session_id, punctuated_text) # CHANGED  11/4/25 9:53am
                if session_id in BUFFER_STORE and BUFFER_STORE[session_id].strip():
                    with time_block(session_id, "punctuate", "flush_buffer"):
                        buffered = BUFFER_STORE.pop(session_id).strip()
                        update_english(db, session_id, buffered)
                await manager.broadcast(session_id, msg)

            # --- HOST LANGUAGE UPDATE ---
            elif source == "host_lang_update":
                with time_block(session_id, "host_lang_update", "update_prefs"):
                    payload = msg.get("payload", {})
                    new_input = payload.get("input")
                    new_output = payload.get("output")
                    update_host_prefs(db, session_id, 1, new_input)
                    update_host_prefs(db, session_id, 2, new_output)
                await manager.broadcast(session_id, msg)

            # --- TRANSLATION TARGET CHANGE ---
            elif source == "translation_target_change":
                with time_block(session_id, "translation_target_change", "update_flag"):
                    payload = msg.get("payload", {})
                    language = payload.get("language")
                    flag = payload.get("FLAG")
                    update_translation_target(db, session_id, language, flag)
                await manager.broadcast(session_id, msg)

            # --- LOCK CONTROL ---
            elif source == "lock":
                IS_PUNCTUATING = True # make session specific
            elif source == "unlock":
                IS_PUNCTUATING = False # make session specific

    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    finally:
        db.close()
