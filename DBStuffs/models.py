from sqlalchemy import Column, String, Text, JSON, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.ext.mutable import MutableDict

Base = declarative_base()

class SessionData(Base):
    __tablename__ = "sessions"

    # These fields exist for *all* session types
    session_id   = Column(String, primary_key=True, unique=True, index=True)
    session_type = Column(String, nullable=False)   # "Host", "CoClient", "Viewer"
    last_updated = Column(DateTime, default=datetime.utcnow)
    active_session = Column(Boolean, default=True)
    archived_FLAG = Column(Boolean, default=False)

    __mapper_args__ = {
        "polymorphic_on": session_type,
        "polymorphic_identity": "base"
    }



class HostSession(SessionData):
    __mapper_args__ = {"polymorphic_identity": "Client"}

    english_transcript    = Column(Text, default="")
    punctuated_transcript = Column(Text, default="")
    translations          = Column(JSON, default=lambda: {"es": "", "fr": "", "de": "", "en": "", "ht": "", "it": "", "zh": "" })

    # TODO ::: LEVEL 5 make the viewer session everytime it connects, add 1 to the data value, if it sees its 0 it will stop translating,
    # TODO ::: LEVEL 5 if it sees it > 1, it will keep translating. if a viewer joins it will go from 1 -> 2, if a viewer leaves, it will go from 1 -> 0
    translation_targets   = Column(MutableDict.as_mutable(JSON), default=lambda: {"en": 0, "es": 1, "fr": 0, "de": 0, "it": 0, "ht": 0, "zh": 0})
    input_lang            = Column(String, default="en-US")
    output_lang           = Column(String, default="English")

class CoClientSession(SessionData):
    __mapper_args__ = {"polymorphic_identity": "CoClient"}

    connected_to_host = Column(String, default="")

    Host1_in_transcript = Column(Text, default="")   #   init the transcript for the spoken transcript on host 1
    Host2_in_transcript = Column(Text, default="")   #   init the transcript for the spoken transcript on host 2
    Host1_out_transcript = Column(Text, default="")  #   init the transcript for the translated transcript on host 1 (what host 1 wants to see on their screen)
    Host2_out_transcript = Column(Text, default="")  #   init the transcript for the translated transcript on host 2 (what host 2 wants to see on their screen)
    Host1_lang_in = Column(Text, default="en")       #   english default for host 1 input language
    Host2_lang_in = Column(Text, default="es")       #   spanish default for host 2 input language
    Host1_lang_out = Column(Text, default="es")      #   english default for host 1 output language (what host 1 wants to see on their screen)
    Host2_lang_out = Column(Text, default="en")      #   spanish default for host 2 output language (what host 2 wants to see on their screen)


class ViewerSession(SessionData):
    __mapper_args__ = {"polymorphic_identity": "Viewer"}

    Viewer_lang = Column(Text, default="en")  # english default for host 1 input language
    # Add whatever Viewer fields you need here.

# to do,
# implement changing the translation langs in the main.py
# finish the other updates with actual db calls
#
#
#
#