import asyncio
import json
import websockets
from datetime import datetime, timedelta
from deepmultilingualpunctuation import PunctuationModel
from DBStuffs.db import SessionLocal, get_or_create_session, init_db
from sqlalchemy import text as sql_text
from analyticTools.timelog import time_block  # ✅ unified timing logger

# -------------------------------------------------------
# Initialize DB (creates tables if they don’t exist)
# -------------------------------------------------------
init_db()

# -------------------------------------------------------
# Initialize the punctuation model
# -------------------------------------------------------
with time_block("137 : punctuator", "load_model", "Loading punctuation model"):
    model = PunctuationModel()

INTERVAL = 5
CONTEXT_WORDS = 20
ACTIVE_WINDOW = 60

# keep per-session progress in memory
last_punct_word_index = {}

# -------------------------------------------------------
# Helper: find new text region
# -------------------------------------------------------
def get_new_region(full_text, session_id):
    """Return the region of text that hasn't yet been punctuated."""
    with time_block(session_id, "get_new_region", "split_words"):
        words = full_text.strip().split()

    start_index = last_punct_word_index.get(session_id, 0)
    if len(words) <= start_index:
        return "", start_index

    with time_block(session_id, "get_new_region", "compute_region"):
        context_start = max(0, start_index - CONTEXT_WORDS)
        region = " ".join(words[context_start:])
        new_index = len(words)
    return region, new_index

# ------ou-------------------------------------------------
# Run punctuation on new region only
# -------------------------------------------------------
async def punctuate(session_id: str):
    """Runs punctuation on the new text delta and sends results to WebSocket."""
    with time_block(session_id, "punctuate", "db_read"):
        db = SessionLocal()
        session = get_or_create_session(db, session_id)
        english_text = (session.english_transcript or "").strip()
        db.close()

    if not english_text:
        print(f"⚠️ No text to punctuate for {session_id}")
        return

    with time_block(session_id, "punctuate", "get_region"):
        region, new_index = get_new_region(english_text, session_id)
    if not region:
        return

    async with websockets.connect(f"ws://127.0.0.1:8000/ws/{session_id}") as ws:
        # --- lock writes ---
        with time_block(session_id, "punctuate", "ws_lock"):
            await ws.send(json.dumps({"source": "lock"}))
        print(f"Locked writes for {session_id}")

        # --- punctuation model ---
        print(f"Running punctuation for {session_id}...")
        try:
            with time_block(session_id, "punctuate", "run_model"):
                punctuated_region = model.restore_punctuation(region)  # big time savings here
        except Exception as e:
            print(f"❌ Punctuation error: {e}")
            await ws.send(json.dumps({"source": "unlock"}))
            return

        # --- send results ---
        with time_block(session_id, "punctuate", "ws_send_punctuated"):
            await ws.send(json.dumps({
                "source": "punctuate",
                "payload": {"english_punctuated": punctuated_region}
            }))
        print(f" Sent new punctuated region for {session_id}")

        # --- unlock ---
        with time_block(session_id, "punctuate", "ws_unlock"):
            await ws.send(json.dumps({"source": "unlock"}))
        print(f" Unlocked writes for {session_id}")

    last_punct_word_index[session_id] = new_index

# -------------------------------------------------------
# Continuous loop
# -------------------------------------------------------
async def loop():
    """Continuously checks for sessions with new text to punctuate."""
    while True:
        with time_block("global", "loop", "db_query_active_sessions"):
            db = SessionLocal()
            cutoff = datetime.utcnow() - timedelta(seconds=ACTIVE_WINDOW)
            results = db.execute(
                sql_text("SELECT session_id, english_transcript FROM sessions WHERE last_updated >= :cutoff"),
                {"cutoff": cutoff}
            ).fetchall()
            db.close()

        # Process each active session
        for sid, english in results:
            english = english.strip() if english else ""
            if english:
                with time_block(sid, "loop", "punctuate_call"):
                    await punctuate(sid)

        await asyncio.sleep(INTERVAL)

# -------------------------------------------------------
# Run
# -------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(loop())