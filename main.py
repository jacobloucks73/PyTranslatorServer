# Main file. run with unicorn,
#
# TODOs are put in order of severity, majors are breaking whole function bugs, level 10s are the most important non-fuctional bugs
# level 1s are trival non functionals
#
# Way the wind blows:
#
# main.py accepts the websockets from the React app. this in turn calls db.py to create a session in the DB using models.py
# depending on DB_type coming from the frontend, there can be a few things different about the overall structure of the table
# this session creation invokes the wrath of the periodic punctuator.py which circles back to every active(60s) session
# for the time being, this punctuate call through the grapevine triggers the translate function to pop. which then calls
# translate into the websocket and sends the translated version back up into the React bullshit web, there are also
# timing gates to make sure nothing gets too rowdy on the timing bit since this is supposedly real time
#
#  -  Smug Alpaca
#
# L0veland is a Canadian, I dont make the rules, get me a bag of milk when you visit your parents
# Sugarbear is love, Sugarbear is life
# Footlocker is the bane of my existence

import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from DBStuffs.db import (
    SessionLocal, update_english, update_translation,
    update_punctuated, init_db, update_host_prefs, update_translation_target, update_CoClient_Input
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

            with time_block(session_id, "websocket_endpoint", "receive"):

                raw = await websocket.receive_text()
                msg = json.loads(raw)
                source = msg.get("source")
                payload = msg.get("payload", {})

            # --- CLIENT SPEECH ---
            if source == "client":

                with time_block(session_id, "client", "update_english"):

                    english_text = payload.get("english", "")

                    if IS_PUNCTUATING: # TODO make session specific

                        BUFFER_STORE[session_id] = BUFFER_STORE.get(session_id, "") + " " + english_text # WTF does this even do

                    else:
                        update_english(db, session_id, english_text)

                await manager.broadcast(session_id, msg)

            if source == "CoClient":

                with time_block(session_id, "CoClient", "update_english"):

                    Client_Num  = payload.get("Client_Num", "") # host num communicating
                    Input_Text  = payload.get("Input", "") # sendToServer("CoClient", { Input: Newly_Committed_Chunk, Host_Num: Client_Number, Host_Lang_Input: Spoken_Lang, Host_Lang_Output: OutputLang}); # TODO put this in the CoClientSession.js after logic is applied
                    # Input_Lang  = payload.get("Host_Lang_Input", "")
                    # Output_Lang = payload.get("Host_Lang_Output", "")

                    if IS_PUNCTUATING: # TODO make session specific
                        BUFFER_STORE[session_id] = BUFFER_STORE.get(session_id, "") + " " + Input_Text # WTF does this even do

                    else:
                       update_CoClient_Input(db, session_id, Input_Text, Client_Num) # TODO add Update_CoClient_Input method to db.py to update backend with Host_Num 1 being host 1 etc...

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
                    await update_punctuated(db, session_id, punctuated_text,"punctuate")
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
