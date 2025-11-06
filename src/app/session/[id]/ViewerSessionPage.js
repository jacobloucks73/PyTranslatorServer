// Place viewer page here not how to get to user page 
// 
// MAKE SOCKETS WORK. so we can have a viewer actually look at the data
// 
// 
// 
// 
// 
// 

"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";

export default function ViewerSessionPage() {
  const { id: sessionId } = useParams(); // get session ID from URL
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputLang, setInputLang] = useState("en-US");
  const [outputLang, setOutputLang] = useState("es");
  const wsRef = useRef(null);

  // Connect to WebSocket server when the viewer loads
  useEffect(() => {
    console.log("Viewer joining session:", sessionId);

  useEffect(() => {
 const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);

  ws.onopen = () => console.log("✅ Connected to server");
  ws.onmessage = (event) => console.log("📨 Received:", JSON.parse(event.data));
  ws.onclose = () => console.log("❌ Disconnected");

  return () => ws.close();
  }, []);

    // (1) Join the session through the API
    async function joinSession() {
      try {
        const res = await fetch("/api/session/join", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sessionId, inputLang, outputLang }),
        });

        const data = await res.json();
        console.log("Viewer joined successfully:", data);
      } catch (err) {
        console.error("Failed to join session:", err);
      }
    }

    joinSession();

    // (2) Simulate a WebSocket connection
    // In production, you'd use `new WebSocket("wss://...")` or Socket.IO
    const ws = {
      send: (msg) => console.log("Mock send:", msg),
      close: () => console.log("Mock close"),
    };
    wsRef.current = ws;
    setConnected(true);

    // (3) Cleanup on page unload
    return () => {
      wsRef.current?.close();
      setConnected(false);
    };
  }, [sessionId, inputLang, outputLang]);

  // (4) Simulate receiving messages from the host
  useEffect(() => {
    const fakeMessage = setInterval(() => {
      setMessages((prev) => [
        ...prev,
        { text: "Translated message from host 🎧", time: new Date().toLocaleTimeString() },
      ]);
    }, 5000);

    return () => clearInterval(fakeMessage);
  }, []);

  return (
    <main className="p-6 flex flex-col items-center space-y-4">
      <h1 className="text-2xl font-bold">Viewer Session</h1>
      <p className="text-gray-600">Session ID: <span className="font-mono">{sessionId}</span></p>
      <p className={connected ? "text-green-600" : "text-red-600"}>
        {connected ? "Connected to Host ✅" : "Disconnected ❌"}
      </p>

      <div className="w-full max-w-xl border rounded p-3 h-64 overflow-y-auto bg-gray-50">
        {messages.length === 0 ? (
          <p className="text-gray-400 italic">Waiting for host to start...</p>
        ) : (
          messages.map((msg, i) => (
            <p key={i} className="mb-1">
              <span className="text-sm text-gray-500">{msg.time}</span> — {msg.text}
            </p>
          ))
        )}
      </div>

      <div className="flex gap-4 mt-4">
        <div>
          <label className="block text-sm font-semibold">Input Language:</label>
          <select
            value={inputLang}
            onChange={(e) => setInputLang(e.target.value)}
            className="border rounded p-1"
          >
            <option value="en-US">English</option>
            <option value="fr-FR">French</option>
            <option value="es-ES">Spanish</option>
            <option value="ht-HT">Haitian Creole</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-semibold">Output Language:</label>
          <select
            value={outputLang}
            onChange={(e) => setOutputLang(e.target.value)}
            className="border rounded p-1"
          >
            <option value="es">Spanish</option>
            <option value="en">English</option>
            <option value="fr">French</option>
            <option value="ht">Haitian Creole</option>
          </select>
        </div>
      </div>
    </main>
  );
}


// speech → WebSocket → DB (raw text) → Punctuation → Translation → DB (updated, multilingual, punctuated)