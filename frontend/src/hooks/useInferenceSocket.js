import { useCallback, useEffect, useRef, useState } from "react";

const WS_URL = (import.meta.env.VITE_WS_URL || "ws://localhost:8000") + "/ws/infer";

export function useInferenceSocket() {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [emotion, setEmotion] = useState("neutral");
  const [confidence, setConfidence] = useState(0);
  const [handDetected, setHandDetected] = useState(false);
  const [tokens, setTokens] = useState([]);
  const [sentence, setSentence] = useState("");
  const [interpreting, setInterpreting] = useState(false);
  const [history, setHistory] = useState([]);
  const [audioUrl, setAudioUrl] = useState(null);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === "frame_result") {
        setEmotion(msg.emotion);
        setConfidence(msg.confidence);
        setHandDetected(msg.hand_detected);
        setTokens(msg.tokens);
        if (msg.should_flush) setInterpreting(true);
      } else if (msg.type === "sentence") {
        setInterpreting(false);
        setTokens([]);
        if (msg.sentence) {
          setSentence(msg.sentence);
          if (msg.history) setHistory(msg.history);
          if (msg.audio) {
            const blob = base64ToBlob(msg.audio, msg.audio_mime || "audio/wav");
            setAudioUrl(URL.createObjectURL(blob));
          }
        }
      } else if (msg.type === "cleared") {
        setTokens([]);
        setSentence("");
        setInterpreting(false);
      }
    };

    return () => ws.close();
  }, []);

  const sendFrame = useCallback((base64Jpeg) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "frame", data: base64Jpeg }));
    }
  }, []);

  const flush = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: "flush" }));
    setInterpreting(true);
  }, []);

  const clear = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: "clear" }));
  }, []);

  return {
    connected, emotion, confidence, handDetected,
    tokens, sentence, interpreting, history, audioUrl,
    sendFrame, flush, clear,
  };
}

function base64ToBlob(base64, mime) {
  const bytes = atob(base64);
  const arr = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
  return new Blob([arr], { type: mime });
}
