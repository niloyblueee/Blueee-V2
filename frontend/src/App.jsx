import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PulseWave from "./components/PulseWave";
import ResearchCanvas from "./components/ResearchCanvas";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:3001";
const HISTORY_STORAGE_KEY = "blueee.chat.history.v1";
const HISTORY_LIMIT = 24;

function normalizeHistory(items) {
  if (!Array.isArray(items)) {
    return [];
  }
  return items
    .map((item) => ({
      role: item?.role === "assistant" ? "assistant" : "user",
      text: String(item?.text || "").trim()
    }))
    .filter((item) => item.text)
    .slice(-HISTORY_LIMIT);
}

function readHistoryFromSessionStorage() {
  try {
    const raw = window.sessionStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    return normalizeHistory(JSON.parse(raw));
  } catch {
    return [];
  }
}

function useSpeechRecognition({ onFinal, onStatus }) {
  const recognitionRef = useRef(null);
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const finalTranscriptRef = useRef("");
  const sentChunksRef = useRef(0);
  const onFinalRef = useRef(onFinal);
  const onStatusRef = useRef(onStatus);

  useEffect(() => {
    onFinalRef.current = onFinal;
    onStatusRef.current = onStatus;
  }, [onFinal, onStatus]);

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
          const clean = text.trim();
          finalTranscriptRef.current = `${finalTranscriptRef.current} ${clean}`.trim();
          console.log("[Speech] Final chunk:", clean);
          sentChunksRef.current += 1;
          onFinalRef.current?.(clean);
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
      sentChunksRef.current = 0;
      setTranscript("");
      console.log("[Speech] Started listening");
      onStatusRef.current?.("Listening...");
    };
    recognition.onend = () => {
      setListening(false);
      const finalText = finalTranscriptRef.current.trim();
      setTranscript(finalText);
      console.log("[Speech] Stopped. Final text:", finalText, "Chunks sent:", sentChunksRef.current);
      
      // Fallback: if no chunks were sent during listening, send full text now
      if (finalText && sentChunksRef.current === 0) {
        console.log("[Speech] Fallback send on stop");
        onFinalRef.current?.(finalText);
      }
      
      finalTranscriptRef.current = "";
      sentChunksRef.current = 0;
      onStatusRef.current?.("Stopped listening.");
    };
    recognition.onerror = (event) => {
      console.error("[Speech] Error:", event.error);
      setListening(false);
      onStatusRef.current?.("Speech recognition error.");
    };

    recognitionRef.current = recognition;

    return () => {
      try {
        recognition.stop();
      } catch {
        // no-op
      }
      recognitionRef.current = null;
    };
  }, []);

  return {
    listening,
    transcript,
    start: () => {
      const recognition = recognitionRef.current;
      if (!recognition || listening) {
        return;
      }
      try {
        recognition.start();
      } catch {
        // no-op
      }
    },
    stop: () => {
      const recognition = recognitionRef.current;
      if (!recognition || !listening) {
        return;
      }
      try {
        recognition.stop();
      } catch {
        // no-op
      }
    }
  };
}

export default function App() {
  const [thinking, setThinking] = useState(false);
  const [canvasContent, setCanvasContent] = useState("");
  const [status, setStatus] = useState("Ready.");
  const [history, setHistory] = useState(() => readHistoryFromSessionStorage());
  const [lastHeard, setLastHeard] = useState("");
  const historyRef = useRef(history);
  const pendingRequestsRef = useRef(0);

  useEffect(() => {
    historyRef.current = history;
  }, [history]);

  const appendHistory = useCallback((role, text) => {
    const cleanText = String(text || "").trim();
    if (!cleanText) {
      return;
    }
    const next = normalizeHistory([...historyRef.current, { role, text: cleanText }]);
    historyRef.current = next;
    setHistory(next);
  }, []);

  const setThinkingByPending = useCallback(() => {
    setThinking(pendingRequestsRef.current > 0);
  }, []);

  useEffect(() => {
    window.sessionStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
  }, [history]);

  const handleFinal = useCallback(async (text) => {
    console.log("[handleFinal] Called with:", text);
    const cleanText = String(text || "").trim();
    if (!cleanText) {
      console.log("[handleFinal] Empty text, skipping");
      return;
    }

    console.log("[handleFinal] Processing:", cleanText);
    setLastHeard(cleanText);
    pendingRequestsRef.current += 1;
    setThinkingByPending();
    setStatus("Blueee is thinking...");

    appendHistory("user", cleanText);
    const nextHistory = historyRef.current;
    console.log("[handleFinal] Sending request with history length:", nextHistory.length);

    try {
      const response = await fetch(`${API_BASE}/api/voice`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          text: cleanText,
          history: nextHistory
        })
      });
      console.log("[handleFinal] Response status:", response.status);
      const payload = await response.json();
      console.log("[handleFinal] Response payload:", payload);

      if (payload?.response?.summary) {
        setCanvasContent(payload.response.summary);
      }

      if (payload?.response?.text) {
        appendHistory("assistant", payload.response.text);
      }

      if (payload?.reply) {
        appendHistory("assistant", payload.reply);
      }

      if (payload?.response?.action === "play_video" && payload?.response?.url) {
        window.open(payload.response.url, "_blank", "noopener,noreferrer");
      }

      setStatus("Standing by.");
      console.log("[handleFinal] Request completed successfully");
    } catch (error) {
      console.error("[handleFinal] Error:", error);
      setStatus("Something went wrong. Check the backend.");
    } finally {
      pendingRequestsRef.current = Math.max(0, pendingRequestsRef.current - 1);
      setThinkingByPending();
    }
  }, [appendHistory, setThinkingByPending]);

  const speechAvailable = useMemo(() => {
    return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
  }, []);

  const { listening, transcript, start, stop } = useSpeechRecognition({
    onFinal: (text) => {
      console.log("[useSpeechRecognition] onFinal fired with:", text);
      handleFinal(text);
    },
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
              {history.slice().reverse().map((item, index) => (
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
