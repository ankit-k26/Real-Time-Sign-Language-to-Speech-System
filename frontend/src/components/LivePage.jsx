import { useEffect, useRef } from "react";
import { useWebcam } from "../hooks/useWebcam";
import { useInferenceSocket } from "../hooks/useInferenceSocket";

export default function LivePage() {
  const videoRef = useRef(null);
  const audioRef = useRef(null);

  const {
    connected, emotion, confidence, handDetected,
    tokens, sentence, interpreting, history, audioUrl,
    sendFrame, flush, clear,
  } = useInferenceSocket();

  useWebcam(videoRef, sendFrame, 150, true);

  useEffect(() => {
    if (audioUrl && audioRef.current) {
      audioRef.current.src = audioUrl;
      audioRef.current.play().catch(() => {});
    }
  }, [audioUrl]);

  useEffect(() => {
    function onKey(e) {
      if (e.code === "Space") { e.preventDefault(); flush(); }
      if (e.key === "c" || e.key === "C") clear();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [flush, clear]);

  return (
    <div className="app-grid">
      <div className="left-panel">
        <div className="video-wrap">
          <video ref={videoRef} autoPlay muted playsInline
                 style={{ transform: "scaleX(-1)" }} />
          <span className={`status-dot ${connected ? "ok" : "bad"}`} />
        </div>
        <div className="subtitle">
          {interpreting ? "⟳ Interpreting..." : (sentence || "Waiting for gesture...")}
        </div>
        <audio ref={audioRef} hidden />
      </div>

      <div className="right-panel">
        <div className="card">
          <h3>Emotion: {emotion.toUpperCase()}</h3>
          <p>Confidence: {(confidence * 100).toFixed(0)}%</p>
          <div className="bar"><div className="bar-fill" style={{ width: `${confidence * 100}%` }} /></div>
          <p>Hand detected: {handDetected ? "yes" : "no"}</p>
        </div>

        <div className="card">
          <h4>Current Tokens</h4>
          <p className="tokens">{tokens.join(" ") || "(no tokens yet)"}</p>
        </div>

        <div className="card history">
          <h4>Conversation History</h4>
          <ul>{history.map((h, i) => <li key={i}>{h}</li>)}</ul>
        </div>

        <div className="btn-row">
          <button onClick={flush}>Translate Now (Space)</button>
          <button onClick={clear} className="danger">Clear Buffer (C)</button>
        </div>
      </div>
    </div>
  );
}
