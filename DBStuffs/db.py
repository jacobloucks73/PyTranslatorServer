import os
from sqlalchemy.orm import Session
from models import SessionData
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import json
import websockets

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
    print("Database initialized (tables ensured).")
    #  creates tables if they don't exist

# -------------------------------------------------
# Create or fetch a session record
# -------------------------------------------------
def get_or_create_session(db: Session, session_id: str):
    session = db.query(SessionData).filter(SessionData.session_id == session_id).first()
    if not session:
        # ✅ ensure session starts active and with timestamps
        session = SessionData(
            session_id=session_id,
            active_session=True,
            last_updated=datetime.utcnow(),
            input_lang="en-US",  #  default input language
            output_lang="English"  #  default output language
           )
        db.add(session)
        db.commit()
        db.refresh(session)
        print(f"Created new active session: {session_id}")
    return session

# -------------------------------------------------
# Append English text instead of overwriting
# -------------------------------------------------
def update_english(db: Session, session_id: str, new_text: str):
    session = get_or_create_session(db, session_id)
    if session.english_transcript:
        session.english_transcript += " " + new_text.strip()
    else:
        session.english_transcript = new_text.strip()

    #  refresh last_updated and mark active if text incoming
    session.last_updated = datetime.utcnow()
    session.active_session = True
    db.commit()

# -------------------------------------------------
# Append translation per language
# -------------------------------------------------
def update_translation(db: Session, session_id: str, lang: str, text: str):
    session = get_or_create_session(db, session_id)
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
async def update_punctuated(db: Session, session_id: str, text: str):
    session = get_or_create_session(db, session_id)
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
    session = get_or_create_session(db, session_id)
    if choser == 1 and session.active_session:
        session.active_session = flag
    elif choser == 2 and session.archived_FLAG:
        session.archived_FLAG = flag

    #  refresh last_updated and mark active again
    session.last_updated = datetime.utcnow()

    db.commit()

def update_translation_target(db: Session, session_id: str, lan:str, flag:bool):
    session = get_or_create_session(db, session_id)
    if   lan == "en":
        session.translation_targets.update({"en": flag})
        print(f"english language selected with flag: {flag} for session ID: {session_id}")
    elif lan == "es":
        session.translation_targets.update({"es": flag})
        print(f"spanish language selected with flag: {flag} for session ID: {session_id}")
    elif lan == "fr":
        session.translation_targets.update({"fr": flag})
        print(f"french language selected with flag: {flag} for session ID: {session_id}")
    elif lan == "de":
        session.translation_targets.update({"de": flag})
        print(f"german language selected with flag: {flag} for session ID: {session_id}")
    elif lan == "ht":
        session.translation_targets.update({"ht": flag})
        print(f"haitian language selected with flag: {flag} for session ID: {session_id}")
    elif lan == "it":
        session.translation_targets.update({"it": flag})
        print(f"Italian language selected with flag: {flag} for session ID: {session_id}")
    elif lan == "zh":
        session.translation_targets.update({"zh": flag})
        print(f"japanese language selected with flag: {flag} for session ID: {session_id}")
    else:
        print("!!!!!! language switch not enabled, lan not found !!!!!!")

    session.last_updated = datetime.utcnow()

    db.commit()

def update_host_prefs(db: Session, session_id: str, choser: int, lan:str):
     session = get_or_create_session(db, session_id)
     if   choser == 1 and lan != "":
         session.input_lang = lan
     elif choser == 2 and lan != "":
         session.output_lang = lan
     #  refresh last_updated and mark active again
     session.last_updated = datetime.utcnow()
     session.active_session = True
     db.commit()
