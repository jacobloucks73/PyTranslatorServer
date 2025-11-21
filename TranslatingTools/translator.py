import os

from analyticTools.timelog import time_block
import asyncio, json, websockets
from DBStuffs.db import SessionLocal, get_or_create_session
from sqlalchemy import text
from datetime import datetime
# from deep_translator import GoogleTranslator
from google.cloud import translate_v2 as translate # for official Google Translate, need API key for test run
from google.oauth2 import service_account
import logging

# Configure loggerf
logger = logging.getLogger("translator")
handler = logging.FileHandler("translator.log")
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False

logger.debug("Translator logger initialized")


INTERVAL = 5                # seconds between live updates
CONTEXT_WORDS = 15          # how many words before new chunk for context
active_sessions = {}        # idk what this does and im to lazy to look

last_punct_word_index1 = {}  # this and the below are for the periodic translation
last_punct_word_index2 = {} # nothing like a temp fix that becomes permanent, get new regions quick fix for multi hostslast_punct_word_index3 = {}  # this and the below are for handle incoming
last_punct_word_index3 = {}
last_punct_word_index4 = {} # nothing like a temp fix that becomes permanent, get new regions quick fix for multi hosts

# Path to service account credentials
# credentials = service_account.Credentials.from_service_account_file(
#     'C:/Users/jacob/Downloads/pyserver-476603-8560f519ac75.json' # path to json file with API key for google translate
#     #  make this a relative path for Loveland and server build
# )

GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

credentials = service_account.Credentials.from_service_account_file(
    GOOGLE_CREDENTIALS_PATH
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
async def translate_text(session_id: str, text_chunk: str, target_lang: str):
    if not text_chunk.strip():
        return ""

    logger.debug(f"Translating: {text_chunk} → {target_lang} @ {datetime.now()}")
    loop = asyncio.get_event_loop()

    # time_block: measure full Google API round trip
    with time_block(session_id, "translate_text_Google_Paid", f"gcloud_{target_lang}"): # timing gates, Ignore
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
            logger.debug(f"❌ Translation error: {e}")
            return

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

def get_new_region(full_text, session_id, yudodis):
    """Return the region of text that hasn't yet been punctuated."""
    global start_index
    with time_block(session_id, "get_new_region", "split_words"):
        words = full_text.strip().split()

    # weird ahh if statement loop I know but it works
    if yudodis == 1:

        start_index = last_punct_word_index1.get(session_id, 0)

    elif yudodis == 2:

        start_index = last_punct_word_index2.get(session_id, 0)

    elif yudodis == 3:

        start_index = last_punct_word_index3.get(session_id, 0)

    elif yudodis == 4:

        start_index = last_punct_word_index4.get(session_id, 0)

    else:
        logger.debug(f"getting here shouldn't be possible : ( : {yudodis}")

    if len(words) <= start_index:
        return "",   start_index

    with time_block(session_id, "get_new_region", "compute_region"):
        context_start = max(0, start_index - CONTEXT_WORDS)
        region = " ".join(words[context_start:])
        new_index = len(words)
    return region, new_index

# -------------------------------------------------------
# Helper: replace overlapping section
# -------------------------------------------------------
def replace_section(session_id: str, old_text: str, new_text: str, overlap_words: int):
    with time_block(session_id, "replace_section", "splice"): # timing gates, Ignore
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
    uri = f"wss://smugalpaca.com/ws/{session_id}"

    async with websockets.connect(uri) as ws:
        logger.debug(f"🌎 Translator connected for session {session_id}")
        # TODO find out why Periodic translations arent going through like periodic punctuates, either get rid of and just do punctuates and translates or vice versa Level 3
        async def periodic_translation():
            global updated_txt_Host_1, updated_txt_Host_2
            while True:
                # 1. Read DB state (english transcript, targets, existing translations)
                with time_block(session_id, "periodic_translation", "db_read"): # timing gates, Ignore
                    db = SessionLocal()
                    try:
                        session = get_or_create_session(db, session_id, "Translator_first_call") # TODO  figure out how to get a DB type here to init the stuff. or if it never inits, create seperate get session method in db.py

                        #TODO get DB_type and use it to integrate the dual client translate feature working with a few if statements

                        SessionType = (session.session_type or "").strip()  # gets session type for use in later calls to DB and Websocket

                        if SessionType == "Client":  # if the session is a single client, do normal shit and things
                            logger.debug("1")
                            english_text = (session.english_transcript or "").strip() #  input text already in the DB, doesnt have to be english
                            targets = dict(session.translation_targets or {})         # TODO : LEVEL 3 : has to be a better way to do this, list of active translation targets, currently never gets revised after the language ends use
                            current_translations = dict(session.translations or {})   # list of translation texts from the translation list

                        elif SessionType == "CoClient":  # if the session is a dual client, do unnormal shit and things

                            Host_1_Input    = (session.Host1_in_transcript or "").strip()   # gets Host Input text 1 from DB
                            Host_2_Input    = (session.Host2_in_transcript or "").strip()   # gets Host input text 2 from DB
                            Host_1_Output    = (session.Host1_out_transcript or "").strip() # gets Host output text 1 from DB
                            Host_2_Output    = (session.Host2_out_transcript or "").strip() # gets Host output text 2 from DB
                            # Host_1_In_Lang  = (session.Host1_lang_in or "en")             # gets the first hosts spoken language, might be useful later
                            # Host_2_In_Lang  = (session.Host2_lang_in or "es")             # gets the second hosts spoken language, might be useful later
                            Host_1_Out_Lang = (session.Host1_lang_out or "es")              # gets the first hosts translated language (what host 1 wants to see on their screen)
                            Host_2_Out_Lang = (session.Host2_lang_out or "en")              # gets the second hosts translated language (what host 2 wants to see on their screen)

                        else:
                            logger.debug(f"the fuck did you enter? {SessionType}")
                            return

                    finally:
                        db.close()

                # 2. Figure out what's new to translate
                with time_block(session_id, "periodic_translation", "region_extract"): # timing gates, Ignore

                    if SessionType == "CoClient":
                        region1, new_index_Host1 = get_new_region(Host_1_Input, session_id,1)    # gets region of new punctuation for host 1
                        region2, new_index_Host2 = get_new_region(Host_2_Input, session_id,2)   # gets region of new punctuation for host 2

                    elif SessionType == "Client":
                        logger.debug("2")
                        region, new_index = get_new_region(english_text, session_id,1)           # gets region of new punctuation for single host

                    else:
                        logger.debug(f"the fuck did you enter? {SessionType}")
                        return

                    if not region and not  region1 and not region2:
                        return

                    # await asyncio.sleep(INTERVAL) # what is this and why was it here before the dual host conversion?
                    # continue

                # 3. Translate into each active language
                if SessionType == "Client":
                    logger.debug("3")
                    for lang_code, is_active in targets.items():
                        if is_active > 0 :

                            logger.debug("4")
                            # translation call
                            with time_block(session_id, "periodic_translation", f"translate_{lang_code}"): # timing gates, Ignore

                                translated = await translate_text(session_id, region, lang_code)

                            # stitch into rolling transcript + broadcast
                            with time_block(session_id, "periodic_translation", f"replace_send_{lang_code}"): # timing gates, Ignore

                                prev_txt = current_translations.get(lang_code, "")
                                updated_txt = replace_section(session_id, prev_txt, translated, CONTEXT_WORDS) # TODO might be a cause of concern in the long run
                                current_translations[lang_code] = updated_txt

                                # host
                                await ws.send(json.dumps({ # send bullshit to the bullshit frontend
                                    "source": "translate",
                                    "payload": {"lang": lang_code, "translated": updated_txt, "sessionID": session_id} # TODO make the frontend match this, make it match SessionIDs
                                }))

                                # viewer
                                await ws.send(json.dumps({  # send bullshit to the bullshit frontend
                                    "source": "translate",
                                    "payload": {"lang": lang_code, "translated": updated_txt, "sessionID": f"{session_id} + 1" }
                                    # TODO make the frontend match this, make it match SessionIDs
                                }))

                elif SessionType == "CoClient":

                    translated_host_2_out = await translate_text(session_id, region1, Host_2_Out_Lang) # translated text for Host 2's output
                    translated_host_1_out = await translate_text(session_id, region2, Host_1_Out_Lang) # translated text for Host 1's output

                    updated_txt_Host_1 = replace_section(session_id, Host_1_Output, translated_host_1_out, CONTEXT_WORDS)  # TODO might be a cause of concern in the long run
                    updated_txt_Host_2 = replace_section(session_id, Host_2_Output, translated_host_2_out, CONTEXT_WORDS)  # TODO might be a cause of concern in the long run

                    await ws.send(json.dumps({ # send bullshit to the bullshit frontend
                        "source": "translate",
                        "payload": {"translated_Host_1":  updated_txt_Host_1, "translated_Host_2":  updated_txt_Host_2, "sessionID": session_id}
                        # TODO make the frontend match this, make it match SessionIDs
                    }))

                else:

                    logger.debug(f"the fuck did you enter? {SessionType}")
                    return


                # 4. Commit updated translations back to DB
                with time_block(session_id, "periodic_translation", "commit"): # timing gates, Ignore

                    db = SessionLocal()

                    if SessionType == "Client":
                        logger.debug("5")
                        try:
                            session = get_or_create_session(db, session_id, "Translate_Client_Call") # change to get session method
                            session.translations = current_translations
                            db.commit()

                        finally:
                            db.close()

                    elif SessionType == "CoClient":

                        try:
                            session = get_or_create_session(db, session_id, "Translate_CoClient_Call")
                            session.Host1_out_transcript = updated_txt_Host_1
                            session.Host2_out_transcript = updated_txt_Host_2
                            db.commit()

                        finally:
                            db.close()

                    else:
                        logger.debug(f"the fuck did you enter? {SessionType}")
                        return

                if SessionType == "Client":
                    logger.debug("6")
                    last_punct_word_index1[session_id] = new_index  # last index for single host gets saved as such

                elif SessionType == "CoClient":

                    last_punct_word_index1[session_id] = new_index_Host1  # last index for host 1 gets saved as such
                    last_punct_word_index2[session_id] = new_index_Host2  # last index for host 2 gets saved as such

                else:

                    logger.debug(f"the fuck did you enter? {SessionType}")
                    return

                # 6. Sleep until next cycle
                await asyncio.sleep(INTERVAL)

        async def handle_incoming():
            # nonlocal last_punct_index, punct_translation, live_translation, last_translated_index

            global Host_2_Punctuated, Host_1_Punctuated
            while True:
                # wait for punctuate call
                with time_block(session_id, "handle_incoming", "recv_ws"): # timing gates, Ignore
                    msg = json.loads(await ws.recv())

                if msg.get("source") != "punctuate":
                    # ignore anything else for now
                    continue

                # pull punctuated english from message
                english_punct = msg["payload"].get("english_punctuated", "") # get single client text region

                if english_punct == "": # if the message is a dual client

                    Host_1_Punctuated = msg["payload"].get("Host_1_punctuated", "")
                    Host_2_Punctuated = msg["payload"].get("Host_2_punctuated", "")
                    SessionType = "CoClient" # we know the message is a coclient at this point

                    if not Host_1_Punctuated and not Host_2_Punctuated:

                        logger.debug("ERROR : how the fuck you get here? ")
                        return

                else:

                    SessionType = "Client"  # we know the message is a single host client at this point
                    logger.debug("7")
                # find delta of punctuated region
                with time_block(session_id, "handle_incoming", "get_region_punctuated"): # timing gates, Ignore

                    if SessionType == "CoClient":

                        region1, new_index_Host1 = get_new_region(Host_1_Punctuated, session_id, 3)  # gets region of new punctuation for host 1
                        region2, new_index_Host2 = get_new_region(Host_2_Punctuated, session_id,4)  # gets region of new punctuation for host 2

                    elif SessionType == "Client":
                        logger.debug("8")
                        region, new_index = get_new_region(english_punct, session_id,3)  # gets region of new punctuation for single host

                    else:

                        logger.debug(f"ERROR : the fuck did you enter? {SessionType}")
                        return

                    if not region and not region1 and not region2:

                        logger.debug(f"ERROR : the fuck did you enter? {region} + {region1} + {region2}")
                        return

                # the fuck is this bullshit?
                # if new_index == last_translated_index:
                #     await asyncio.sleep(INTERVAL)
                #     continue

                # reload DB targets + translations
                with time_block(session_id, "handle_incoming", "db_read_again"): # timing gates, Ignore
                    db = SessionLocal()
                    try:

                        session = get_or_create_session(db, session_id, "Translate_handle_incoming")

                        if SessionType == "Client":
                            logger.debug("9")
                            targets = dict(session.translation_targets or {})
                            current_translations = dict(session.translations or {})

                        elif SessionType == "CoClient":

                            # Host_1_Input = (session.Host1_in_transcript or "").strip()  # gets Host Input text 1 from DB
                            # Host_2_Input = (session.Host2_in_transcript or "").strip()  # gets Host input text 2 from DB
                            Host_1_Output = (session.Host1_out_transcript or "").strip()  # gets Host output text 1 from DB
                            Host_2_Output = (session.Host2_out_transcript or "").strip()  # gets Host output text 2 from DB
                            # Host_1_In_Lang  = (session.Host1_lang_in or "en")           # gets the first hosts spoken language, might be useful later
                            # Host_2_In_Lang  = (session.Host2_lang_in or "es")           # gets the second hosts spoken language, might be useful later
                            Host_1_Out_Lang = (session.Host1_lang_out or "es")            # gets the first hosts translated language (what host 1 wants to see on their screen)
                            Host_2_Out_Lang = (session.Host2_lang_out or "en")            # gets the second hosts translated language (what host 2 wants to see on their screen)

                        else:

                            logger.debug(f"the fuck did you enter? {SessionType}")
                            return

                    finally:
                        db.close()

                if SessionType == "Client":
                    logger.debug("10")
                    for lang_code, is_active in targets.items():

                        if is_active > 0:

                            with time_block(session_id, "handle_incoming", f"translate_punct_{lang_code}"):    # timing gates, Ignore

                                prev_txt = current_translations.get(lang_code, "")                             # gets the full text from db
                                translated = await translate_text(session_id, region, lang_code)               # actual translate
                                updated_txt = replace_section(session_id, prev_txt, translated, CONTEXT_WORDS) # TODO look at this to find if it is fucking up
                                current_translations[lang_code] = updated_txt                                  # updates DB

                                # push back out to clients
                                await ws.send(json.dumps({
                                    "source": "translate",
                                    "payload": {"lang": lang_code, "translated": updated_txt}
                                }))



                elif SessionType == "CoClient":

                    translated_host_2_out = await translate_text(session_id, region1, Host_2_Out_Lang) # translated text for Host 2's output
                    translated_host_1_out = await translate_text(session_id, region2, Host_1_Out_Lang) # translated text for Host 1's output

                    updated_txt_Host_1 = replace_section(session_id, Host_1_Output, translated_host_1_out, CONTEXT_WORDS)  # TODO might be a cause of concern in the long run
                    updated_txt_Host_2 = replace_section(session_id, Host_2_Output, translated_host_2_out, CONTEXT_WORDS)  # TODO might be a cause of concern in the long run

                    await ws.send(json.dumps({ # send bullshit to the bullshit frontend
                        "source": "translate",
                        "payload": {"translated_Host_1":  updated_txt_Host_1, "translated_Host_2":  updated_txt_Host_2, "sessionID": session_id}
                        # TODO make the frontend match this, make it match SessionIDs
                    }))

                else:

                    logger.debug(f"the fuck did you enter? {SessionType}")
                    return

                db = SessionLocal()

                if SessionType == "Client":
                    logger.debug("12")
                    try:
                        session = get_or_create_session(db, session_id, "Translate_Client_Call")  # change to get session method
                        session.translations = current_translations
                        db.commit()

                    finally:
                        db.close()

                elif SessionType == "CoClient":

                    try:
                        session = get_or_create_session(db, session_id, "Translate_CoClient_Call")
                        session.Host1_out_transcript = updated_txt_Host_1
                        session.Host2_out_transcript = updated_txt_Host_2
                        db.commit()

                    finally:
                        db.close()

                else:
                    logger.debug(f"the fuck did you enter? {SessionType}")
                    return

                if SessionType == "Client":
                    logger.debug("13")
                    last_punct_word_index3[session_id] = new_index  # last index for single host gets saved as such

                elif SessionType == "CoClient":

                    last_punct_word_index3[session_id] = new_index_Host1  # last index for host 1 gets saved as such
                    last_punct_word_index4[session_id] = new_index_Host2  # last index for host 2 gets saved as such

                else:

                    logger.debug(f"the fuck did you enter? {SessionType}")
                    return

        await asyncio.gather(periodic_translation(), handle_incoming())


async def safe_translator_session(sid):
    try:
        db = SessionLocal()
        get_or_create_session(db, sid, "safe_translator")
        db.close()
        await translator_session(sid)
    except Exception as e:
        logger.debug(f"⚠️ Translator for {sid} crashed: {e}")
    finally:
        if sid in active_sessions:
            del active_sessions[sid]


# -------------------------------------------------------
# Manager loop: spawn per-session translators
# -------------------------------------------------------
async def manager_loop():
    while True:

        with time_block("manager", "manager_loop", "query_sessions"): # timing gates, Ignore
            db = SessionLocal()
            results = db.execute(
                text("SELECT session_id, last_updated FROM sessions WHERE english_transcript != '' AND active_session = TRUE")
            ).fetchall()
            resultsDos = db.execute(
                text("SELECT session_id, last_updated FROM sessions WHERE Host2_in_transcript != '' AND Host1_in_transcript != '' AND active_session = TRUE;")
            ).fetchall()
            db.close()

            for SessionID, LastUpdated in results:
                logger.debug("session ID : " + SessionID + ". last updated : " + LastUpdated)
                # TODO get periodic translation working by adding logic here to continue filtering session data by cutoff time
                # if last updated = current - 60 secs, make inactive
                task = asyncio.create_task(safe_translator_session(SessionID))
                active_sessions[SessionID] = task
            for SessionID, LastUpdated in resultsDos:
                loggerlogger.debug("session ID : " + SessionID + ". last updated : " + LastUpdated)
                # TODO get periodic translation working by adding logic here to continue filtering session data by cutoff time
                # if last updated = current - 60 secs, make inactive
                # then call periodic translator here


        await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(manager_loop())
    except KeyboardInterrupt:
        for sid, task in active_sessions.items():
            task.cancel()