// add QR code to get to viewer for the session. 
// add session key very big 
// 
// 
// 
// 
// 
// 
// 
// 
// 
// 
// 
// 
// 
// 
// 
// speech → WebSocket → DB (raw text) → Punctuation → Translation → DB (updated, multilingual, punctuated)
// 
export default function DisplayPage() {
  const { id } = useParams();
  const searchParams = useSearchParams();
  const roleParam = searchParams.get("role");
  const sessionKey = searchParams.get("key");

  const [isHost, setIsHost] = useState(roleParam ? roleParam === "host" : null);
  const [sessionId, setsessionId] = useState(id || "");
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [listening, setListening] = useState(false);

  // 🗣️ Language selectors
  const [spokenLang, setSpokenLang] = useState("en-US");   // host microphone input
  const [targetLang, setTargetLang] = useState("es");      // host translation output
  const [viewerLang, setViewerLang] = useState("es");      // viewer display

  const recognitionRef = useRef(null);
  const wsRef = useRef(null);
  const fullEnglishRef = useRef("");
  const fullSpanishRef = useRef("");
