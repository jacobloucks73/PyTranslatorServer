"use client";

//  TO DO:
// 
// Add language function to switch output language while in host session
// add way to go to Display page(QR code, Session Key, Viewer count, ETC...)
// add web sockets so viewers can actually get to the host and vice versa
// pass language to translators so they can translate any language given
// get from database every 4 secs. 
 


// const response = await fetch("/api/translate", {
//   method: "POST",
//   headers: { "Content-Type": "application/json" },
//   body: JSON.stringify({
//     text: englishTranscript, // 👈 your transcript string
//     lan: "es",               // 👈 target language (e.g., "es" for Spanish)
//   }),
// });

// const data = await response.json();
// console.log("Translated text:", data.translation);
// 
// above is call to translate for route.js in translate

import { useState, useRef, useEffect } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { Filter } from "bad-words";

const englishFilter = new Filter();
const spanishFilter = new Filter();

const LANG_OPTIONS = [
  { code: "en", label: "English" },
  { code: "es", label: "Spanish" },
  { code: "de", label: "German" },
  { code: "fr", label: "French" },
  { code: "it", label: "Italian" },
  { code: "ht", label: "Haitian Creole"},
  { code: "zh", label: "Chinese" },
  { code: "ja", label: "Japanese" },
];

export default function SessionPage() {
  const { id } = useParams();
  const searchParams = useSearchParams();
  const roleParam = searchParams.get("role");
  const sessionKey = searchParams.get("key");

  const [isHost, setIsHost] = useState(roleParam ? roleParam === "host" : null);
  const [sessionId, setsessionId] = useState(id || "");
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [lastInput, setlastInput] = useState("");
  const [lastOutput, setlastOutput] = useState("");
  const [listening, setListening] = useState();

  // 🗣️ Language selectors
  const [spokenLang, setSpokenLang] = useState("en-US");   // host microphone input
  const [targetLang, setTargetLang] = useState("es");      // host translation output
  const [viewerLang, setViewerLang] = useState("es");      // viewer display


  const recognitionRef = useRef(null);
  const wsRef = useRef(null);
  const fullEnglishRef = useRef("");
  const fullSpanishRef = useRef("");
  const targetLangRef = useRef(targetLang);
  const lastInputRef = useRef(lastInput);  // Initialize with an empty string
  const lastOutputRef = useRef(lastOutput);  // Initialize with an empty string

useEffect(() => {
  targetLangRef.current = targetLang;
}, [targetLang]);
useEffect(() => {
  lastInputRef.current = lastInput;
}, [lastInput]);
useEffect(() => {
  lastOutputRef.current = lastOutput;
}, [lastOutput]);

useEffect(() => {
  if (!sessionId) {
    console.log("ERROR: No session ID found");
    return;
  }
   if (wsRef.current) {
    //console.log("🔁 Closing old WS for session:", wsRef.current.sessionId);
    wsRef.current.close(1000, "Switching session");
    wsRef.current = null;
  }

  const ws = new WebSocket(`ws://127.0.0.1:8000/ws/${sessionId}`);
  wsRef.current = ws;

    ws.onopen = () => {
      //console.log("✅ WS connected");
      // send current language prefs when connecting
      if (isHost)
        ws.send(JSON.stringify({ source: "host_lang_update", payload: { input: spokenLang, output: targetLang } }));
      else
        ws.send(JSON.stringify({ source: "host_lang_update", payload: { output: viewerLang } }));
    };

ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        //console.log("📨 WS:", msg);

        switch (msg.source) {
           case "client":
          //console.log("input set to:" + msg.payload.english_punctuated); 
          setInput(msg.payload.english_punctuated); break;
          case "punctuate": 
          // console.log("input set to:" + msg.payload.english_punctuated); // setInput(msg.payload.english_punctuated); break;
          case "translate": 
          //console.log(targetLangRef.current + " == " + msg.payload.lang)
          if (targetLangRef.current ==  msg.payload.lang){
          //console.log("output set to:" + msg.payload.translated)
          setOutput(msg.payload.translated); // look out of dupe info?
          break;
          }

          case "host_lang_update":
          case "translation_target_change":
            console.log("✅ Language update received:", msg.payload);
            break;
          default: console.warn("⚠️ Unknown message source:", msg.source);
        }
      } catch (err) { console.error("❌ WS error:", err); }
    };

 return () => {
    if (ws.readyState === WebSocket.OPEN) ws.close(1000, "Cleanup");
    wsRef.current = null;
  };
}, [sessionId]);

  // ✅ Setup filters
  useEffect(() => {
    spanishFilter.addWords(
      "puta", "mierda", "cabron", "coño", "pendejo", "chingar",
      "culero", "gilipollas", "joder", "hostia", "maldito"
    );
    englishFilter.addWords(
      "fuck", "shit", "bitch", "asshole", "nigger", "cunt", "faggot", "cock",
      "pussy", "dick", "slut", "whore", "nigga"
    );
  }, []);

  // add more filters for the other languages 
  
function cleanText(text, lang = spokenLang) {
  if (!text) return "";
  if (lang === "en"){ return englishFilter.clean(text);}
  if (lang === "es") {return spanishFilter.clean(text);} // have to change this to have more vars and ifs when switching input lan to var
  else return englishFilter.clean(text);
}

function sendToServer(type, payload) {
  if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
  wsRef.current.send(JSON.stringify({ source: type, payload }));
}

function startListening() {
    if (typeof window === "undefined") return;

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition not supported in this browser.");
      return;
    }

    // CHANGED  11/4/25 9:59am
    setInput(fullEnglishRef.current);
    console.log("input: " + fullEnglishRef.current);
    setOutput(fullSpanishRef.current);
    console.log("output: " + fullSpanishRef.current);

    // fullEnglishRef.current = "";
    // fullSpanishRef.current = "";
    setListening(true);

    if (recognitionRef.current) recognitionRef.current.stop();

    const recognition = new SpeechRecognition();
    recognition.lang = spokenLang; //en-US is default, is this changing automatically without reload?  11/4/25 9:57am
    recognition.continuous = true;
    recognition.interimResults = true;
    recognitionRef.current = recognition;

    recognition.onresult = (event) => {
      let committed = fullEnglishRef.current || "";
      let interim = "";
      let newlyCommittedChunk = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const raw = event.results[i][0].transcript || "";
        const safe = cleanText(raw, "en").trim();

        if (event.results[i].isFinal) {
          if (safe) {
            committed += (committed ? " " : "") + safe;
            newlyCommittedChunk += (newlyCommittedChunk ? " " : "") + safe;
          }
        } else {
          interim = safe;
        }
      }

      // ✅ Send finalized chunk to backend
      if (newlyCommittedChunk && wsRef.current?.readyState === WebSocket.OPEN) {
        sendToServer("client", { english: newlyCommittedChunk });
      }
      // might be useful for debugging, gives you the chunks on the input log
      fullEnglishRef.current = committed;
      const display = [committed, interim].filter(Boolean).join(" ");

      console.log(display)
      // does this work now?
      setInput(display);
    };

   recognition.onerror = (event) => {
  console.error("Speech recognition error:", event.error || event, event.message || "");
  alert(`Speech recognition error: ${event.error || "unknown"} — check console`);
  setListening(false);
};


    recognition.onend = () => setListening(false);
    recognition.start();
  }


// 🛑 Stop listening
function stopListening() {
  recognitionRef.current?.stop();
  // clearTimeout(window.punctuateTimer); // 🧹 clean up WHY IS THIS VALID SYNTAX?!?!?
  //console.log("00000\n")
  setlastInput(input);  // Store the current input into lastInputRef
  fullSpanishRef = output.current;
  console.log("input: " + fullEnglishRef.current)
  console.log("output: " + fullSpanishRef.current)
  setInput("");
  setOutput("");
  setListening(false);
}
  return (
    <main className="p-8 max-w-xl mx-auto space-y-6">
      <h1 className="text-3xl font-bold text-center mb-4">
        Session Code: {sessionId}
      </h1>

      {/* Step 1: Role Selection */}
      {isHost === null && (
        <div className="text-center">
          <p className="mb-4 text-gray-700">
            Are you the host or a viewer for this translation session?
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={() => setIsHost(true)}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
            >
              🎤 I am the Host
            </button>
            <button
              onClick={() => setIsHost(false)}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              👀 I am a Viewer
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Host Interface */}
      {isHost === true && (
        <>
          <h2 className="text-xl font-semibold text-center">
            Host: Real-Time Translator
          </h2>

          {/* 🌐 Language Selectors */}
          <div className="flex justify-center gap-4 my-4">
            <div>
              <label className="block text-sm font-semibold mb-1">
                Spoken Language:
              </label>
              <select
                value={spokenLang}
                onChange={(e) => {
                  const val = e.target.value;
                  setSpokenLang(val);
                  sendToServer("host_lang_update", { input: val, output: targetLang });
                }}
                className="border rounded p-2"
              >
                {LANG_OPTIONS.map((l) => (
                  <option
                    key={l.code}
                    value={`${l.code}-${l.code.toUpperCase()}`}
                  >
                    {l.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold mb-1">
                Translate To:
              </label>
              <select
                value={targetLang}
                onChange={(e) => {
                  const val = e.target.value;
              
                  sendToServer("translation_target_change", { language: val, FLAG: true });
                }}
                className="border rounded p-2"
              >
                {LANG_OPTIONS.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Input / Output Text Boxes */}
          <div>
            <label className="block font-semibold mb-1">
              Recognized ({spokenLang.toUpperCase()}):
            </label>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
               className="w-full border p-3 rounded bg-gray-100 text-gray-900 min-h-[600px] max-h-[1000px] overflow-y-auto"
            />
          </div>

          <div>
            <label className="block font-semibold mb-1">
              Translation ({targetLang.toUpperCase()}):
            </label>
            <div
              className="w-full border p-3 rounded bg-gray-100 text-gray-900 min-h-[600px] max-h-[1000px] overflow-y-auto"
            >
              {output || "Translation will appear here..."}
            </div>
          </div>

{/* Start / Stop Listening */}
<div className="flex gap-3 justify-center mt-4">
  {!listening ? (
    <button
      onClick={() => {
        startListening();  // Start listening
      }}
      className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
    >
      🎤 Start Listening
    </button>
  ) : (
    <button
      onClick={() => {
        stopListening();  // Stop listening
      }}
      className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
    >
      ⏹ Stop
    </button>
  )}
</div>
        </>
      )}

      {/* Step 3: Viewer Interface */}
      {isHost === false && (
        <>
          <h2 className="text-xl font-semibold text-center">
            Viewer: Live Translation Feed
          </h2>

          {/* 🌐 Viewer Language Selector */}
          <div className="flex justify-center gap-4 mb-4">
            <div>
              <label className="block text-sm font-semibold mb-1">
                Display Language:
              </label>
              <select
                value={viewerLang}
                onChange={(e) => {
                  const val = e.target.value;
                  setViewerLang(val);
                  sendToServer("host_lang_update", { input: "", output: val });
                }}
                className="border rounded p-2"
              >
                {LANG_OPTIONS.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Translation Output Box */}
          <div
            className="w-full border p-3 rounded bg-gray-100 text-gray-900 min-h-[150px] max-h-[300px] overflow-y-auto"
          >
            {output || "Waiting for translation..."}
          </div>
        </>
      )}
    </main>
  );
}
  // speech → WebSocket → DB (raw text) → Punctuation → Translation → DB (updated, multilingual, punctuated)