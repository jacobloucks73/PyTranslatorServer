import os
from sqlalchemy.orm import Session
# from models import *
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# from models import Base
import json
import websockets
from DBStuffs.models import *
import logging

# Configure logging

logger = logging.getLogger("DB")
handler = logging.FileHandler("DB.log")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# -------------------------------------------------
# Initialize the database
# -------------------------------------------------
def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.debug("Database initialized (tables ensured).")
    #  creates tables if they don't exist

from datetime import datetime

def get_or_create_session(db: Session, session_id: str, DB_Type: str):
    session = db.query(SessionData).filter(SessionData.session_id == session_id).first() # the fuck is this error?
    if session:
        return session  # already exists → return it

    type_map = {
        "Client": HostSession,
        "CoClient": CoClientSession,
        "Viewer": ViewerSession,
    }

    cls = type_map.get(DB_Type)
    if cls is None:
        raise ValueError(f"Unknown session type '{DB_Type}'. Must be Client, CoClient, or Viewer.")

    # ✅ Create the correct subclass
    session = cls(
        session_id=session_id,
        session_type=DB_Type,        # not required if subclass is set up correctly,
                                     # but safe to include
        last_updated=datetime.utcnow(),
        active_session=True
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    logger.debug(f"Created new {DB_Type} session: {session_id}")
    return session

# -------------------------------------------------
# Append English text instead of overwriting
# -------------------------------------------------
def update_english(db: Session, session_id: str, new_text: str):
    logger.debug("reached db.py update_english")
    init_db()
    logger.debug("reached db.py get or create session")
    session = get_or_create_session(db, session_id, DB_Type="Client")
    logger.debug("Updated english text for session " + session_id)
    if session.english_transcript:
        session.english_transcript += " " + new_text.strip()
    else:
        session.english_transcript = new_text.strip()

    logger.debug("Updated english text for session : " + session.english_transcript)
    #  refresh last_updated and mark active if text incoming
    session.last_updated = datetime.utcnow()
    session.active_session = True
    db.commit()

# -------------------------------------------------
# Append translation per language for single Host / Viewer sessions
# -------------------------------------------------
def update_translation(db: Session, session_id: str, lang: str, text: str):
    session = get_or_create_session(db, session_id, DB_Type= "Client")
    translations = session.translations or {}

    if translations.get(lang):
        translations[lang] = translations[lang].strip() + " " + text.strip()
    else:
        translations[lang] = text.strip()

    session.translations = translations
    session.last_updated = datetime.utcnow()
    db.commit()

# -------------------------------------------------
# Append punctuated transcript (not overwrite)
# -------------------------------------------------
async def update_punctuated(db: Session, session_id: str, text: str, DB_type: str):
    session = get_or_create_session(db, session_id, DB_Type= DB_type)  #  TODO add the CoClient pathway to the punctuator.py file to be able to see the DB to see if it is a CoClient or not
    if session.punctuated_transcript:
        session.punctuated_transcript += " " + text.strip()
    else:
        session.punctuated_transcript = text.strip()

    #  refresh last_updated and mark active again
    session.last_updated = datetime.utcnow()
    session.active_session = True

    db.commit()
    async with websockets.connect(f"ws://127.0.0.1:8000/ws/{session_id}") as ws:

        await ws.send(json.dumps({
            "source": "client",
            "payload": {"english_punctuated": session.punctuated_transcript}
        }))

def update_flag(db: Session, session_id: str, choser:int, flag:bool):
    session = get_or_create_session(db, session_id, "update_flag")
    if choser == 1 and session.active_session:
        session.active_session = flag
    elif choser == 2 and session.archived_FLAG:
        session.archived_FLAG = flag

    #  refresh last_updated and mark active again
    session.last_updated = datetime.utcnow()

    db.commit()

def update_translation_target(db: Session, session_id: str, lan:str, flag:bool):
    # session = get_or_create_session(db, session_id, "update_translation_target")
    # if   lan == "en":
    #     # newNum = session.translation_targets.get(lan)
    #     session.translation_targets.update({"en": flag})
    #     logger.debug(f"english language selected with flag: {flag} for session ID: {session_id}")
    # elif lan == "es":
    #     session.translation_targets.update({"es": flag})
    #     logger.debug(f"spanish language selected with flag: {flag} for session ID: {session_id}")
    # elif lan == "fr":
    #     session.translation_targets.update({"fr": flag})
    #     logger.debug(f"french language selected with flag: {flag} for session ID: {session_id}")
    # elif lan == "de":
    #     session.translation_targets.update({"de": flag})
    #     logger.debug(f"german language selected with flag: {flag} for session ID: {session_id}")
    # elif lan == "ht":
    #     session.translation_targets.update({"ht": flag})
    #     logger.debug(f"haitian language selected with flag: {flag} for session ID: {session_id}")
    # elif lan == "it":
    #     session.translation_targets.update({"it": flag})
    #     loggerlogger.debug(f"Italian language selected with flag: {flag} for session ID: {session_id}")
    # elif lan == "zh":
    #     session.translation_targets.update({"zh": flag})
    #     logger.debug(f"japanese language selected with flag: {flag} for session ID: {session_id}")
    # else:
    #     logger.debug("!!!!!! language switch not enabled, lan not found !!!!!!")

    session = get_or_create_session(db, session_id, "update_translation_target")

    if lan not in session.translation_targets:
        logger.debug("!!!!!! language switch not enabled, lan not found !!!!!!")
        return

    # Get current value
    current_value = session.translation_targets.get(lan, 0)

    # Compute new value (True = +1, False = -1)
    delta = 1 if flag else -1
    new_value = current_value + delta

    # Update the stored value
    session.translation_targets[lan] = new_value

    session.last_updated = datetime.utcnow()

    db.commit()

def update_host_prefs(db: Session, session_id: str, choser: int, lan:str):
     session = get_or_create_session(db, session_id,"Client")
     if   choser == 1 and lan != "":
         session.input_lang = lan
     elif choser == 2 and lan != "":
         session.output_lang = lan
     #  refresh last_updated and mark active again
     session.last_updated = datetime.utcnow()
     session.active_session = True
     db.commit()

def update_CoClient_Lang(db: Session, session_id: str, Input_Lang: str,Output_Lang: str, Client_Num: int):

    session = get_or_create_session(db, session_id, "Co-Client_Input")

    if Client_Num == 1:

        if Input_Lang != "":

            session.Host1_lang_in = Input_Lang

        if Output_Lang != "":

            session.Host1_lang_in = Output_Lang


    if Client_Num == 2:

        if Input_Lang != "":
            session.Host2_lang_in = Input_Lang

        if Output_Lang != "":

            session.Host2_lang_in = Output_Lang

    else:

        logger.debug(f"the fuck did you enter? {Client_Num}")
        return

    session.active_session = True
    db.commit()

def update_CoClient_Input(db: Session, session_id: str, Input_Text: str, Client_Num: int):

    session = get_or_create_session(db, session_id, "CoClient")

    if Client_Num == 1:

        session.Host1_in_transcript = Input_Text

    elif Client_Num == 2:

        session.Host2_in_transcript = Input_Text

    else:

        logger.debug(f"the fuck did you enter? {Client_Num}")
        return

    session.active_session = True
    db.commit()

def initViewer(db: Session, session_id: str):

    session = get_or_create_session(db, session_id, "Viewer")

    # TODO ::: LEVEL 6 ::: make the lang update on the host side when the viewer connects so the host starts

    session.active_session = True
    db.commit()