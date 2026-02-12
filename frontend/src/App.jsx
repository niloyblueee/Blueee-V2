import { useEffect, useMemo, useRef, useState } from "react";
import PulseWave from "./components/PulseWave";
import ResearchCanvas from "./components/ResearchCanvas";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:3001";

function useSpeechRecognition({ onFinal, onStatus }) {
  const recognitionRef = useRef(null);
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const finalTranscriptRef = useRef("");

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const text = result[0]?.transcript || "";
        if (result.isFinal && text.trim()) {
          finalTranscriptRef.current = `${finalTranscriptRef.current} ${text}`.trim();
          onFinal(text.trim());
        } else {
          interim = `${interim} ${text}`.trim();
        }
      }
      const merged = `${finalTranscriptRef.current} ${interim}`.trim();
      setTranscript(merged);
    };

    recognition.onstart = () => {
      setListening(true);
      finalTranscriptRef.current = "";
      setTranscript("");
      onStatus?.("Listening...");
    };
    recognition.onend = () => {
      setListening(false);
      setTranscript(finalTranscriptRef.current);
      onStatus?.("Stopped listening.");
    };
    recognition.onerror = () => {
      setListening(false);
      onStatus?.("Speech recognition error.");
    };

    recognitionRef.current = recognition;
  }, [onFinal, onStatus]);

  return {
    listening,
    transcript,
    start: () => recognitionRef.current?.start(),
    stop: () => recognitionRef.current?.stop()
  };
}

export default function App() {
  const [thinking, setThinking] = useState(false);
  const [canvasContent, setCanvasContent] = useState("");
  const [status, setStatus] = useState("Ready.");
  const [history, setHistory] = useState([]);
  const [lastHeard, setLastHeard] = useState("");

  const handleFinal = async (text) => {
    setLastHeard(text);
    setThinking(true);
    setStatus("Blueee is thinking...");
    setHistory((prev) => [{ role: "user", text }, ...prev].slice(0, 6));

    try {
      const response = await fetch(`${API_BASE}/api/voice`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ text })
      });
      const payload = await response.json();

      if (payload?.response?.summary) {
        setCanvasContent(payload.response.summary);
      }

      if (payload?.response?.text) {
        setHistory((prev) => [{ role: "assistant", text: payload.response.text }, ...prev].slice(0, 6));
      }

      if (payload?.reply) {
        setHistory((prev) => [{ role: "assistant", text: payload.reply }, ...prev].slice(0, 6));
      }

      if (payload?.response?.action === "play_video" && payload?.response?.url) {
        window.open(payload.response.url, "_blank", "noopener,noreferrer");
      }

      setStatus("Standing by.");
    } catch (error) {
      setStatus("Something went wrong. Check the backend.");
    } finally {
      setThinking(false);
    }
  };

  const speechAvailable = useMemo(() => {
    return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
  }, []);

  const { listening, transcript, start, stop } = useSpeechRecognition({
    onFinal: handleFinal,
    onStatus: setStatus
  });

  useEffect(() => {
    const handlePlayVideo = (event) => {
      const url = event?.detail?.url;
      if (url) {
        window.open(url, "_blank", "noopener,noreferrer");
      }
    };

    window.addEventListener("play_video", handlePlayVideo);
    return () => window.removeEventListener("play_video", handlePlayVideo);
  }, []);

  const startListening = () => {
    if (!speechAvailable) {
      setStatus("Speech recognition not available in this browser.");
      return;
    }
    setStatus("Listening...");
    start();
  };

  const stopListening = () => {
    stop();
    setStatus("Stopped listening.");
  };

  const waveActive = listening || thinking;
  const listenLabel = listening ? "Listening" : "Start Listening";
  const stopDisabled = !listening && !thinking;

  return (
    <div className="min-h-screen bg-night text-slate-100">
      <div className="flex items-center justify-between border-b border-white/5 px-8 py-5">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-plasma/70">Blueee V2</p>
          <h1 className="text-2xl font-semibold text-white">Cyberpunk-Minimalist Console</h1>
        </div>
        <div className="text-xs uppercase tracking-[0.3em] text-slate-500">Web Mode</div>
      </div>

      <div className="grid gap-6 px-8 py-8 lg:grid-cols-[1.1fr_1.6fr]">
        <section className="glass-panel rounded-3xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Voice Interface</h2>
              <p className="text-sm text-slate-400">Say a command or ask for research.</p>
            </div>
            <PulseWave active={waveActive} />
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              className={`rounded-full px-5 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-night ${
                listening
                  ? "bg-ember shadow-[0_0_25px_rgba(255,122,24,0.5)]"
                  : "bg-plasma"
              }`}
              onClick={startListening}
              disabled={listening}
            >
              {listenLabel}
            </button>
            <div className="flex items-center gap-2 text-[0.65rem] uppercase tracking-[0.3em] text-slate-400">
              <span
                className={`h-2 w-2 rounded-full ${listening ? "bg-ember" : "bg-slate-600"}`}
              />
              {listening ? "Recording" : "Idle"}
            </div>
            <button
              className={`rounded-full border px-5 py-2 text-xs uppercase tracking-[0.3em] ${
                stopDisabled
                  ? "border-white/5 text-white/30"
                  : "border-white/10 text-white/80"
              }`}
              onClick={stopListening}
              disabled={stopDisabled}
            >
              Stop
            </button>
          </div>

          <div className="mt-6 rounded-2xl border border-white/5 bg-obsidian/70 p-4">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Live Transcript</p>
            <p className="mt-3 text-sm text-white/90">
              {transcript || lastHeard || "Waiting for voice input..."}
            </p>
          </div>

          <div className="mt-5 text-xs uppercase tracking-[0.3em] text-plasma/70">
            {status}
          </div>
        </section>

        <section className="space-y-6">
          <div className="glass-panel rounded-3xl p-6">
            <h2 className="text-lg font-semibold">Command Timeline</h2>
            <div className="mt-4 space-y-3">
              {history.length === 0 && (
                <p className="text-sm text-slate-400">No commands yet.</p>
              )}
              {history.map((item, index) => (
                <div
                  key={`${item.role}-${index}`}
                  className="rounded-2xl border border-white/5 bg-obsidian/70 p-3"
                >
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
                    {item.role}
                  </p>
                  <p className="mt-2 text-sm text-white/90">{item.text}</p>
                </div>
              ))}
            </div>
          </div>

          <ResearchCanvas content={canvasContent} />
        </section>
      </div>
    </div>
  );
}
