from sqlalchemy import Column, String, Text, JSON, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

from sqlalchemy.ext.mutable import MutableDict

Base = declarative_base()


class SessionData(Base):
    __tablename__ = "sessions"

    session_id            = Column(String,    primary_key=True, unique=True, index=True)
    english_transcript    = Column(Text,      default="") # used for main transcript no matter what lan right now
    punctuated_transcript = Column(Text,      default="")
    translations          = Column(JSON,      default=lambda: {"es": "", "fr": "", "de": "", "en": "", "ht": "", "it": "", "zh": ""})
    translation_targets   = Column(MutableDict.as_mutable(JSON),      default=lambda: {"en": False, "es": True,"fr": False,"de": False,"it": False,"ht": False,"zh": False})
    last_updated          = Column(DateTime,  default=datetime.utcnow)
    input_lang            = Column(String,    default="en-US")     # hosts current input language
    output_lang           = Column(String,    default="English")   # hosts current output lang
    archived_FLAG         = Column(Boolean,   default=False)      # host decides if  he wants to  archive and end the conversation
    active_session        = Column(Boolean,   default=True)      # keeps track if it is an active session

# to do,
# implement changing the translation langs in the main.py
# finish the other updates with actual db calls
#
#
#
#