import { useRef, useState, useCallback } from "react";
import { useWebcam } from "../hooks/useWebcam";

const WS_URL = (import.meta.env.VITE_WS_URL || "ws://localhost:8000") + "/ws/collect";

export default function CollectPage() {
  const videoRef = useRef(null);
  const wsRef = useRef(null);
  const [word, setWord] = useState("");
  const [numSequences, setNumSequences] = useState(30);
  const [collecting, setCollecting] = useState(false);
  const [progress, setProgress] = useState({ frame: 0, total: 30, seqNum: 0 });
  const [log, setLog] = useState([]);

  const ensureSocket = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return wsRef.current;
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "collect_progress") {
        setProgress((p) => ({ ...p, frame: msg.frame, total: msg.total }));
        if (msg.sequence_done) {
          setLog((l) => [`✓ Sequence saved for '${msg.word}'`, ...l]);
        }
      }
    };
    return ws;
  }, []);

  // Streams frames continuously while `collecting` is true; the backend
  // only writes them to disk once start_sequence() has been called.
  useWebcam(videoRef, (b64) => {
    const ws = wsRef.current;
    if (collecting && ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "frame", data: b64 }));
    }
  }, 66, true); // ~15fps while recording sequences

  async function recordSequences() {
    if (!word.trim()) return;
    const ws = ensureSocket();
    if (ws.readyState !== WebSocket.OPEN) {
      await new Promise((resolve) => (ws.onopen = resolve));
    }

    for (let s = 0; s < numSequences; s++) {
      setProgress({ frame: 0, total: 30, seqNum: s + 1 });
      ws.send(JSON.stringify({ type: "start_sequence", word }));
      setCollecting(true);
      await waitForSequenceDone();
      setCollecting(false);
      await new Promise((r) => setTimeout(r, 300)); // brief pause, mirrors time.sleep(0.3)
    }
    setLog((l) => [`[DONE] Collected ${numSequences} sequences for '${word}'`, ...l]);
  }

  function waitForSequenceDone() {
    return new Promise((resolve) => {
      const ws = wsRef.current;
      const handler = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === "collect_progress" && msg.sequence_done) {
          ws.removeEventListener("message", handler);
          resolve();
        }
      };
      ws.addEventListener("message", handler);
    });
  }

  return (
    <div className="collect-page">
      <h2>Collect Gesture Data</h2>
      <p>Browser equivalent of <code>collect_data.py --word "hello" --sequences 30</code></p>

      <video ref={videoRef} autoPlay muted playsInline style={{ transform: "scaleX(-1)", width: 480 }} />

      <div className="collect-controls">
        <input placeholder="word / sign label" value={word}
               onChange={(e) => setWord(e.target.value)} disabled={collecting} />
        <input type="number" value={numSequences}
               onChange={(e) => setNumSequences(Number(e.target.value))} disabled={collecting} />
        <button onClick={recordSequences} disabled={collecting || !word.trim()}>
          {collecting ? `Recording seq ${progress.seqNum}...` : "Start Recording"}
        </button>
      </div>

      {collecting && (
        <div className="bar"><div className="bar-fill" style={{ width: `${(progress.frame / progress.total) * 100}%` }} /></div>
      )}

      <ul className="collect-log">{log.map((l, i) => <li key={i}>{l}</li>)}</ul>
    </div>
  );
}
