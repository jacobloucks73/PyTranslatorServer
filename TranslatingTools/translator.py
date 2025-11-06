from analyticTools.timelog import time_block
import asyncio, json, websockets
from DBStuffs.db import SessionLocal, get_or_create_session
from sqlalchemy import text
from datetime import datetime
# from deep_translator import GoogleTranslator
from google.cloud import translate_v2 as translate # for official google translate, need API key for test run
from google.oauth2 import service_account

INTERVAL = 1          # seconds between live updates
CONTEXT_WORDS = 15    # how many words before new chunk for context
active_sessions = {}

# Path to your service account credentials
credentials = service_account.Credentials.from_service_account_file(
    'C:/Users/jacob/Downloads/pyserver-476603-8560f519ac75.json' # path to json file with API key for google translate
)

# Initialize the Translate client
translator = translate.Client(credentials=credentials)

# -------------------------------------------------------
# Helper: call OpenAI
# -------------------------------------------------------
#
# async def translate_text(session_id: str, text: str, target_lang: str):
#     if not text.strip():
#         return ""
#
#     print(f"[{datetime.now()}] Translating '{text}' → {target_lang}")
#     loop = asyncio.get_event_loop()
#
#     # time_block measures the full API call duration end-to-end
#     with time_block(session_id, "translate_text_OpenAI_paid", f"openai_{target_lang}"):
#         try:
#             res = await loop.run_in_executor(
#                 None,
#                 lambda: client.chat.completions.create(
#                     model="gpt-4o-mini",
#                     messages=[
#                         {"role": "system", "content": "You are a professional translator."},
#                         {"role": "user", "content": f"Translate to {target_lang}:\n{text}"},
#                     ],
#                 ),
#             )
#
#             # Return the translated text
#             return res.choices[0].message.content.strip()
#
#         except Exception as e:
#             print(f"❌ Translation error: {e}")
#             return ""

# -------------------------------------------------------
# Helper: call GooglePaid
# -------------------------------------------------------
#
async def translate_text(session_id: str, text_chunk: str, target_lang: str):
    if not text_chunk.strip():
        return ""

    print(f"Translating: {text_chunk} → {target_lang} @ {datetime.now()}")
    loop = asyncio.get_event_loop()

    # time_block: measure full Google API round trip
    with time_block(session_id, "translate_text_Google_Paid", f"gcloud_{target_lang}"):
        try:
            # Run the blocking Google Translate call in a thread pool
            result = await loop.run_in_executor(
                None,
                lambda: translator.translate(
                    text_chunk,
                    target_language=target_lang,   # e.g. 'es', 'fr', 'de'
                    source_language = None,          # auto-detects source
                    format_="text"                 # can also be "html"
                )
            )

            # The API returns a dict, so extract the translated text
            translated_text = result["translatedText"]
            return translated_text.strip()

        except Exception as e:
            print(f"❌ Translation error: {e}")
            return ""

# -------------------------------------------------------
# Helper: call GoogleFree
# -------------------------------------------------------
#
# async def translate_text(session_id: str, text_chunk: str, target_lang: str): # measure time for paid google API vs free one
#     if not text_chunk.strip():
#         return ""
#
#     print("Translating: " + text_chunk + " into " + target_lang + " @ " + datetime.now())
#     loop = asyncio.get_event_loop()
#
#     # prompt = f"Translate {text_chunk} to {target_lang}. output JUST the translation"
#
#     # time_block: how long the OpenAI API call takes end-to-end
#     with time_block(session_id, "translate_text_Google_Free", f"google_{target_lang}"):
#         try:
#             result = await loop.run_in_executor(
#                 None,
#                 lambda:GoogleTranslator(source='auto', target=target_lang).translate(text_chunk)
#             )
#             return result
#
#         except Exception as e:
#             print(f"❌ Translation error: {e}")
#             return ""


# -------------------------------------------------------
# Helper: find new words + context
# -------------------------------------------------------

def get_new_region(session_id: str, full_text: str, last_index: int):
    # measure splitting text into words
    with time_block(session_id, "get_new_region", "split"):
        words = full_text.strip().split()

    if len(words) <= last_index:
        return "", last_index  # nothing new

    # measure building the "region" window
    with time_block(session_id, "get_new_region", "window_build"):
        start_idx = max(0, last_index - CONTEXT_WORDS)
        region = " ".join(words[start_idx:])
        new_index = len(words)

    return region, new_index


# -------------------------------------------------------
# Helper: replace overlapping section
# -------------------------------------------------------
def replace_section(session_id: str, old_text: str, new_text: str, overlap_words: int):
    with time_block(session_id, "replace_section", "splice"):
        old_words = old_text.strip().split()
        if overlap_words > len(old_words):
            overlap_words = len(old_words)

        trimmed = " ".join(old_words[:-overlap_words]) if overlap_words else old_text
        merged = (trimmed + " " + new_text).strip()

    return merged


# -------------------------------------------------------
# Main loop for a single session
# -------------------------------------------------------
async def translator_session(session_id: str):
    uri = f"ws://127.0.0.1:8000/ws/{session_id}"

    last_translated_index = 0
    last_punct_index = 0
    live_translation = ""
    punct_translation = ""

    async with websockets.connect(uri) as ws:
        print(f"🌎 Translator connected for session {session_id}")

        async def periodic_translation():
            nonlocal last_translated_index
            while True:
                # 1. Read DB state (english transcript, targets, existing translations)
                with time_block(session_id, "periodic_translation", "db_read"):
                    db = SessionLocal()
                    try:
                        session = get_or_create_session(db, session_id)
                        english_text = (session.english_transcript or "").strip()
                        targets = dict(session.translation_targets or {})          # {"es": True, ...}
                        current_translations = dict(session.translations or {})    # {"es": "...", ...}
                    finally:
                        db.close()

                # 2. Figure out what's new to translate
                with time_block(session_id, "periodic_translation", "region_extract"):
                    region, new_index = get_new_region(session_id, english_text, last_translated_index)

                # no new words? skip
                if new_index == last_translated_index:
                    await asyncio.sleep(INTERVAL)
                    continue

                # 3. Translate into each active language
                for lang_code, is_active in targets.items():
                    if not is_active:
                        continue

                    # translation call
                    with time_block(session_id, "periodic_translation", f"translate_{lang_code}"):
                        #print("383 : set to translate" + region)
                        translated = await translate_text(session_id, region, lang_code)

                    # stitch into rolling transcript + broadcast
                    with time_block(session_id, "periodic_translation", f"replace_send_{lang_code}"):
                        prev_txt = current_translations.get(lang_code, "")
                        updated_txt = replace_section(session_id, prev_txt, translated, CONTEXT_WORDS)
                        current_translations[lang_code] = updated_txt

                        await ws.send(json.dumps({
                            "source": "translate",
                            "payload": {"lang": lang_code, "translated": updated_txt}
                        }))

                # 4. Commit updated translations back to DB
                with time_block(session_id, "periodic_translation", "commit"):
                    db = SessionLocal()
                    try:
                        s = get_or_create_session(db, session_id)
                        s.translations = current_translations
                        db.commit()
                    finally:
                        db.close()

                # 5. Advance pointer so we don't re-translate the same text
                last_translated_index = new_index

                # 6. Sleep until next cycle
                await asyncio.sleep(INTERVAL)

        async def handle_incoming():
            nonlocal last_punct_index, punct_translation, live_translation, last_translated_index

            while True:
                # wait for downstream events (like punctuate)
                with time_block(session_id, "handle_incoming", "recv_ws"):
                    msg = json.loads(await ws.recv())

                if msg.get("source") != "punctuate":
                    # ignore anything else for now
                    continue

                # pull punctuated english from message
                english_punct = msg["payload"].get("english_punctuated", "")
                words = english_punct.strip().split()
                if len(words) <= last_punct_index:
                    continue

                # find delta of punctuated region
                with time_block(session_id, "handle_incoming", "get_region_punctuated"):
                    region, new_index = get_new_region(session_id, english_punct, last_punct_index)

                # no new meaningful text? skip
                if new_index == last_translated_index:
                    await asyncio.sleep(INTERVAL)
                    continue

                # update the punct index so we don't resend
                last_punct_index = new_index

                # reload DB targets + translations
                with time_block(session_id, "handle_incoming", "db_read_again"):
                    db = SessionLocal()
                    try:
                        session = get_or_create_session(db, session_id)
                        targets = dict(session.translation_targets or {})
                        current_translations = dict(session.translations or {})
                    finally:
                        db.close()

                # translate this punctuated region into each active target language
                for lang_code, is_active in targets.items():
                    if not is_active:
                        continue

                    with time_block(session_id, "handle_incoming", f"translate_punct_{lang_code}"):
                        prev_txt = current_translations.get(lang_code, "")
                       #+ print ("459 : set to translate" +  region)
                        translated = await translate_text(session_id, region, lang_code)
                        updated_txt = replace_section(session_id, prev_txt, translated, CONTEXT_WORDS)
                        current_translations[lang_code] = updated_txt

                        # push back out to clients
                        await ws.send(json.dumps({
                            "source": "translate",
                            "payload": {"lang": lang_code, "translated": updated_txt}
                        }))

                # persist post-punctuation translations
                with time_block(session_id, "handle_incoming", "commit_punctuated"):
                    db = SessionLocal()
                    try:
                        s = get_or_create_session(db, session_id)
                        s.translations = current_translations
                        db.commit()
                    finally:
                        db.close()

                # keep our main pointer in sync with new_index so periodic loop won't re-translate
                last_translated_index = new_index

        await asyncio.gather(periodic_translation(), handle_incoming())


async def safe_translator_session(sid):
    try:
        db = SessionLocal()
        get_or_create_session(db, sid)
        db.close()
        await translator_session(sid)
    except Exception as e:
        print(f"⚠️ Translator for {sid} crashed: {e}")
    finally:
        if sid in active_sessions:
            del active_sessions[sid]


# -------------------------------------------------------
# Manager loop: spawn per-session translators
# -------------------------------------------------------
async def manager_loop():
    while True:
        # gather list of sessions that have any english text
        with time_block("manager", "manager_loop", "query_sessions"):
            db = SessionLocal()
            results = db.execute(
                text("SELECT session_id FROM sessions WHERE english_transcript != ''")
            ).fetchall()
            db.close()

        session_ids = []
        for row in results:
            if isinstance(row, (tuple, list)):
                session_ids.append(row[0])
            elif hasattr(row, "_mapping"):
                session_ids.append(row._mapping.get("session_id"))
            else:
                session_ids.append(str(row))

        # for each session, ensure we have a running translator task
        for sid in session_ids:
            if sid not in active_sessions:
                task = asyncio.create_task(safe_translator_session(sid))
                active_sessions[sid] = task

        await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(manager_loop())
    except KeyboardInterrupt:
        for sid, task in active_sessions.items():
            task.cancel()
