"use client";

import {useState} from "react";
import {useRouter} from "next/navigation";

// const englishFilter = new Filter();
// const spanishFilter = new Filter();

export default function Home() {
  const router = useRouter();

  // 🔧 State variables
  const [inputLang, setInputLang] = useState("en-US");
  const [outputLang, setOutputLang] = useState("es");
  const [isPrivate, setIsPrivate] = useState(false);
  const [creating, setCreating] = useState(false);
  
async function handleCreateSession() {
  setCreating(true);
  try {
    const response = await fetch("/api/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ inputLang, outputLang, isPrivate }),
    });

    const data = await response.json();
    var sessionKey = data.sessionId;

    // ✅ Conditional redirect

      router.push(`/session/${sessionKey}?role=host`)
  } catch (err) {
    console.error("Failed to create session:", err);
    alert("Error creating session.");
  } finally {
    setCreating(false);
  }
}

async function handleJoinSession(ArchivalJoin) {
  const sessionId = prompt("Enter session ID to join:");
  try{
  const response = await fetch("/api/session/join", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId, inputLang, outputLang }),
  });
  const data = await response.json();
  router.push(`/session/${sessionId}?role=viewer`);
}
catch (err) {
      console.error("Failed to join session:", err);
      alert("Error joining session.");
    }
  }

  return (
    <div className="space-y-3">
  <label className="block font-semibold">Input Language:</label>
  <select
    value={inputLang}
    onChange={(e) => setInputLang(e.target.value)}
    className="w-full border p-2 rounded"
  >
    <option value="en-US">English (US)</option>
    <option value="fr-FR">French</option>
    <option value="de-DE">German</option>
    <option value="es-ES">Spanish</option>
    <option value="ht-HT">Haitian</option>
  </select>

  <label className="block font-semibold mt-3">Output Language:</label>
  <select
    value={outputLang}
    onChange={(e) => setOutputLang(e.target.value)}
    className="w-full border p-2 rounded"
  >
    <option value="es">Spanish</option>
    <option value="en">English</option>
    <option value="fr">French</option>
    <option value="de">German</option>
    <option value="ht">Haitian</option>
  </select>

  <div className="flex items-center gap-2 mt-2">
    <input
      type="checkbox"
      checked={isPrivate}
      onChange={(e) => setIsPrivate(e.target.checked)}
    />
    <label>Private Session (requires key)</label>
  </div>

  {/* 👇 Host or Viewer Selection */}
  <div className="flex justify-center gap-4 mt-3">
    <button
      onClick={() => handleCreateSession()}
      className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
    >
      I am the Host
    </button>
    <button
      onClick={() => handleJoinSession()}
      className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
    >
      I am a Viewer
    </button>
    <button
      onClick={() => handleJoinSession(true)}
      className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
    >
      I am a Archival Viewer 
    </button>

  </div>
</div>
  );
}


