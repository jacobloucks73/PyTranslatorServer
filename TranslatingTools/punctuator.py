# import asyncio
# import json
# import websockets
# from datetime import datetime, timedelta
# from deepmultilingualpunctuation import PunctuationModel
# from DBStuffs.db import SessionLocal, get_or_create_session, init_db
# from sqlalchemy import text as sql_text
# from analyticTools.timelog import time_block  # ✅ unified timing logger
# import logging
# from RedisBus import publish
#
#
# # Configure logging
#
# logger = logging.getLogger("punctuator")
# handler = logging.FileHandler("punctuator.log")
# logger.addHandler(handler)
# logger.setLevel(logging.DEBUG)
# # Log messages
#
# logger.debug('Reached punctuator')
# ##
# ## MAJOR TODO Integrate this into main.py to parallelize the punctuate functions for different sessions
# ## TODO might need to copy current objects after initial deeplanguagemodel cause it costs thirty seconds each time
# ##
#
# # Initialize DB (creates tables if they don’t exist)
# init_db()
#
# # Initialize the punctuation model
# with time_block("27 : punctuator", "load_model", "Loading punctuation model"):
#     model = PunctuationModel()
#
# INTERVAL = 5
# CONTEXT_WORDS = 20
# ACTIVE_WINDOW = 60
#
# # keep per-session progress in memory
# last_punct_word_index = {}
# last_punct_word_index2 = {} # nothing like a temp fix that becomes permanent, getnew regions quick fix for multi hosts
#
# # -------------------------------------------------------
# # Helper: find new text region
# # -------------------------------------------------------
# def get_new_region(full_text, session_id):
#     """Return the region of text that hasn't yet been punctuated."""
#     with time_block(session_id, "get_new_region", "split_words"):
#         words = full_text.strip().split()
#
#     start_index = last_punct_word_index.get(session_id, 0)
#     if len(words) <= start_index:
#         return "", start_index
#
#     with time_block(session_id, "get_new_region", "compute_region"):
#         context_start = max(0, start_index - CONTEXT_WORDS)
#         region = " ".join(words[context_start:])
#         new_index = len(words)
#     return region, new_index
#
#
# # i know its lazy but it works lmao
# def get_new_region2(full_text, session_id):
#     """Return the region of text that hasn't yet been punctuated."""
#     with time_block(session_id, "get_new_region", "split_words"):
#         words = full_text.strip().split()
#
#     start_index = last_punct_word_index2.get(session_id, 0)
#     if len(words) <= start_index:
#         return "", start_index
#
#     with time_block(session_id, "get_new_region", "compute_region"):
#         context_start = max(0, start_index - CONTEXT_WORDS)
#         region = " ".join(words[context_start:])
#         new_index = len(words)
#     return region, new_index
#
#
# async def punctuate(session_id: str):
#
#     """Runs punctuation on the new text delta and sends results to WebSocket."""
#     with time_block(session_id, "punctuate", "db_read"): # timing gates, Ignore
#
#         db = SessionLocal()
#         session = get_or_create_session(db, session_id, "punctuator call")           # gets session with session ID or creates session
#
#         SessionType = (session.session_type or "").strip()        # gets session type for use in later calls to DB and Websocket
#
#         if SessionType == "Client": # if bitches want to party alone
#             logger.debug("1")
#             english_text = (session.english_transcript or "").strip() # gets english text from DB
#
#             if not english_text:
#                 logger.debug(f"⚠️ No text to punctuate for {session_id}")
#                 return
#
#         elif SessionType == "CoClient": # if bitches want to party with someone else
#
#             Host_1_Input = (session.Host1_in_transcript or "").strip() # gets Host Input 1 from DB
#             Host_2_Input = (session.Host2_in_transcript or "").strip()  # gets Host input 2 from DB
#
#             if not Host_1_Input.strip() and not Host_2_Input.strip():
#                 logger.debug(f"⚠️ No text to punctuate for {session_id}")
#                 return
#
#         else:
#
#             logger.debug(f"the fuck did you enter? {SessionType}")
#             return
#
#         db.close() # after path has been chosen, close DB
#
#
#     with time_block(session_id, "punctuate", "get_region"): # timing gates, Ignore
#
#         if SessionType == "CoClient":
#
#             region1, new_index_Host1 = get_new_region(Host_1_Input, session_id)  # gets region of new punctuation for host 1
#             region2, new_index_Host2 = get_new_region2(Host_2_Input, session_id) # gets region of new punctuation for host 2
#
#             if not region1.strip() and not region2.strip():
#                 return
#
#         elif SessionType == "Client":
#             logger.debug("2")
#             region, new_index = get_new_region(english_text, session_id)         # gets region of new punctuation for single host
#
#             if not region.strip():
#                 return
#
#         else:
#             logger.debug(f"the fuck did you enter? {SessionType}")
#             return
#
#     async with websockets.connect(f"wss://smugalpaca.com/ws/{session_id}") as ws:
#         # --- lock writes ---
#         with time_block(session_id, "punctuate", "ws_lock"): # timing gates, Ignore
#             await ws.send(json.dumps({"source": "lock"})) # very confused on why this is here? for buffer locks maybe?
#
#         logger.debug(f"Locked writes for {session_id}")
#
#         # --- punctuation model ---
#         logger.debug(f"Running punctuation for {SessionType}, {session_id}...")
#
#         try:
#             with time_block(session_id, "punctuate", "run_model"): # big time savings here
#
#                 if SessionType == "CoClient":
#                     punctuated_region1 = model.restore_punctuation(region1)  # brains for punctuating host 1s region
#                     punctuated_region2 = model.restore_punctuation(region2)  # brains for punctuating host 2s region
#
#                 elif SessionType == "Client":
#                     logger.debug("3")
#                     punctuated_region = model.restore_punctuation(region)  # brains for punctuating single host region
#
#                 else:
#                     logger.debug(f"the fuck did you enter? {SessionType}")
#                     return
#
#         except Exception as e:
#             logger.debug(f"❌ Punctuation error: {e}")
#             await ws.send(json.dumps({"source": "unlock"}))
#             return
#
#         # --- send results ---
#         with time_block(session_id, "punctuate", "ws_send_punctuated"): # timing gates, Ignore
#
#             if SessionType == "Client": # send websocket to single client
#                 logger.debug("4")
#                 await ws.send(json.dumps({
#                     "source": "punctuate",
#                     "payload": {"english_punctuated": punctuated_region, "sessionID": session_id}
#                 }))
#
#                 await ws.send(json.dumps({
#                     "source": "punctuate",
#                     "payload": {"english_punctuated": punctuated_region, "sessionID": f"{session_id}1"}
#                 }))
#
#             elif SessionType == "CoClient":
#                 await ws.send(json.dumps({
#                     "source": "punctuate",
#                     "payload": {"Host_1_punctuated": punctuated_region1, "Host_2_punctuated": punctuated_region2, "sessionID": session_id}
#                     # MAJOR TODO update frontend CoClientSessionPage to accept dual input
#                     # MAJOR TODO update frontend to ignore non matching sessionIDs
#                 }))
#
#             else:
#                 logger.debug(f"the fuck did you enter? {SessionType}")
#                 return
#
#             logger.debug(f" Sent new punctuated region for {session_id}")
#
#         # --- unlock ---
#         with time_block(session_id, "punctuate", "ws_unlock"): # timing gates, Ignore
#             await ws.send(json.dumps({"source": "unlock"}))
#         logger.debug(f" Unlocked writes for {session_id}")
#
#     if SessionType == "Client":
#         logger.debug("5")
#         last_punct_word_index[session_id] = new_index # last index for single host gets saved as such
#
#     elif SessionType == "CoClient":
#         last_punct_word_index[session_id] = new_index_Host1  # last index for host 1 gets saved as such
#         last_punct_word_index2[session_id] = new_index_Host2 # last index for host 2 gets saved as such
#
#     else:
#         logger.debug(f"the fuck did you enter? {SessionType}")
#         return
#
#
# # -------------------------------------------------------
# # Continuous loop
# # -------------------------------------------------------
# async def loop():
#     """Continuously checks for sessions with new text to punctuate."""
#     while True:
#         with time_block("global", "loop", "db_query_active_sessions"): # timing gates, Ignore
#             db = SessionLocal()
#             cutoff = datetime.utcnow() - timedelta(seconds=ACTIVE_WINDOW)
#             results = db.execute(
#                 sql_text("SELECT session_id, english_transcript FROM sessions WHERE last_updated >= :cutoff"),
#                 {"cutoff": cutoff}
#             ).fetchall()
#
#
#             resultsDos = db.execute( # MAJOR : validate if this works, im not sure my sql is right here
#                 sql_text("SELECT session_id, Host1_in_transcript, Host2_in_transcript FROM sessions WHERE last_updated >= :cutoff"),
#                 {"cutoff": cutoff}
#             ).fetchall()
#         db.close()
#
#         # Process each active session
#         for sid, english in results:
#             english = english.strip() if english else ""
#             if english:
#                 with time_block(sid, "loop", "punctuate_call"): # timing gates, Ignore
#                     await punctuate(sid)
#
#         # In theory should get the not empty dual sessions and start a punctuate on them
#         for sid, english1, english2 in resultsDos:
#             english1 = english1.strip() if english1 else ""
#             english2 = english2.strip() if english2 else ""
#             if english1 or english2:
#                 with time_block(sid, "loop", "punctuate_Dos_call"): # timing gates, Ignore
#                     await punctuate(sid)
#
#         await asyncio.sleep(INTERVAL)
#
# # -------------------------------------------------------
# # Run
# # -------------------------------------------------------
# if __name__ == "__main__":
#     asyncio.run(loop())
import asyncio
#import json
import logging
#from datetime import datetime
from deepmultilingualpunctuation import PunctuationModel

from DBStuffs.db import SessionLocal, get_or_create_session
from analyticTools.timelog import time_block
from RedisBus import subscribe, publish

logging.basicConfig(
    filename="punctuator.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("punctuator")

# -------------------------------------------------------
# Load punctuation model ONCE (global)
# -------------------------------------------------------
with time_block("PUNCTUATOR", "startup", "load_model"):
    model = PunctuationModel()

# per-session index bookkeeping
last_idx_host1 = {}
last_idx_host2 = {}

CONTEXT_WORDS = 20


# -------------------------------------------------------
# Helper: extract new region based on last seen index
# -------------------------------------------------------
def get_region(text: str, last_idx: int):
    words = text.strip().split()
    if len(words) <= last_idx:
        return "", last_idx

    start = max(0, last_idx - CONTEXT_WORDS)
    region = " ".join(words[start:])
    return region, len(words)


# -------------------------------------------------------
# Process SINGLE HOST punctuation
# -------------------------------------------------------
async def handle_single_host(msg):
    session_id = msg["session_id"]
    english = msg["payload"].get("english", "").strip()
    if not english:
        return

    region, new_idx = get_region(english, last_idx_host1.get(session_id, 0))
    if not region:
        return

    try:
        with time_block(session_id, "punctuator_single", "model"):
            punctuated = model.restore_punctuation(region)
    except Exception as e:
        logger.debug(f"Model error (single host): {e}")
        return

    # save new index
    last_idx_host1[session_id] = new_idx

    # broadcast through Redis
    await publish("punctuate_output", {
        "sessionID": session_id,
        "payload": {
            "english_punctuated": punctuated
        }
    })


# -------------------------------------------------------
# Process CO-CLIENT punctuation
# -------------------------------------------------------
async def handle_dual_host(msg):
    session_id = msg["session_id"]
    client_num = msg["payload"].get("Client_Num")
    text = msg["payload"].get("Input", "").strip()

    if not text:
        return

    if client_num == 1:
        region, new_idx = get_region(text, last_idx_host1.get(session_id, 0))
        if not region:
            return

        with time_block(session_id, "punctuator_dual", "model_host1"):
            punct = model.restore_punctuation(region)

        last_idx_host1[session_id] = new_idx

        await publish("punctuate_output", {
            "sessionID": session_id,
            "payload": {
                "Host_1_punctuated": punct,
                "Host_2_punctuated": ""
            }
        })

    elif client_num == 2:
        region, new_idx = get_region(text, last_idx_host2.get(session_id, 0))
        if not region:
            return

        with time_block(session_id, "punctuator_dual", "model_host2"):
            punct = model.restore_punctuation(region)

        last_idx_host2[session_id] = new_idx

        await publish("punctuate_output", {
            "sessionID": session_id,
            "payload": {
                "Host_1_punctuated": "",
                "Host_2_punctuated": punct
            }
        })


# -------------------------------------------------------
# MAIN WORKER LOOP
# -------------------------------------------------------
async def main():
    logger.debug("Punctuator worker listening…")

    # Listen to both single-host and co-client speech
    async for msg in subscribe(["raw_speech_input", "coclient_raw_speech_input"]):

        try:
            channel = msg.get("channel")
            if channel == "raw_speech_input":
                await handle_single_host(msg)

            elif channel == "coclient_raw_speech_input":
                await handle_dual_host(msg)

        except Exception as e:
            logger.debug(f"Worker error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.debug("Punctuator shutdown")
