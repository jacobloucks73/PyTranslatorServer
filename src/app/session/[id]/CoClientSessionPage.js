// To Do : 
// 
// make the page so a client-client connection can exist
// thinl of an install between two different language speakers 
// we want them to see their transcript, their translated output and their co-clients translated transcript
// so three text boxes in total 
// maybe some type of debug feature 
// 
// 
// 
// 
// 
// 
// 
// 


export default function CoClientSessionPage() {
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
