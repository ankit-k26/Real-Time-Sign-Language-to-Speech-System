"""
FastAPI backend for the Sign Language to Speech System.

Replaces gui.py (PyQt5 desktop app) entirely. The browser owns the webcam
and streams frames in; this process owns the model, MediaPipe detectors,
the LangChain/Ollama interpreter, and TTS synthesis.

WebSocket protocol (JSON text frames both ways):
  Client -> Server on /ws/infer:
    {"type": "frame", "data": "<base64 jpeg>"}
    {"type": "flush"}   # manual "Translate Now" (mirrors Space key in gui.py)
    {"type": "clear"}   # mirrors 'C' key in gui.py
  Server -> Client:
    {"type": "frame_result", "emotion", "confidence", "hand_detected", "new_word", "tokens", "should_flush"}
    {"type": "sentence", "sentence", "tokens", "history", "audio": "<base64>", "audio_mime"}

  Client -> Server on /ws/collect:
    {"type": "start_sequence", "word": "hello"}
    {"type": "frame", "data": "<base64 jpeg>"}
  Server -> Client:
    {"type": "collect_progress", "word", "frame", "total", "hand_detected", "sequence_done"}
"""

import base64
import json
import os

from dotenv import load_dotenv
load_dotenv()  # loads backend/.env into os.environ

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from .services.collect_service import CollectSession
from .services.inference_service import ModelRegistry, SignSession
from .services.tts_service import TTSService

app = FastAPI(title="Sign Language to Speech API")

_raw_origins = os.environ.get("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

tts_service = TTSService()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABEL_MAP_PATH = os.path.join(BASE_DIR, "models", "model_meta.json")


def decode_frame(b64_data: str) -> np.ndarray:
    """base64 JPEG/PNG string -> BGR numpy array (what cv2 expects)."""
    raw = base64.b64decode(b64_data.split(",")[-1])  # strip data URL prefix if present
    arr = np.frombuffer(raw, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Could not decode frame")
    return frame


# ── REST ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/labels")
def labels():
    """Returns the trained model's gesture label map."""
    if not os.path.exists(LABEL_MAP_PATH):
        return {"labels": [], "note": "Model not trained yet."}
    with open(LABEL_MAP_PATH) as f:
        meta = json.load(f)
    return {"labels": list(meta["label_map"].values())}


@app.post("/tts")
async def synthesize(payload: dict):
    """Standalone TTS endpoint, useful for replaying history entries."""
    text = payload.get("text", "")
    audio_bytes, mime = await run_in_threadpool(tts_service.synthesize, text)
    return {
        "audio": base64.b64encode(audio_bytes).decode("ascii"),
        "mime": mime,
    }


# ── WebSocket: live inference ────────────────────────────────────────────

@app.websocket("/ws/infer")
async def ws_infer(websocket: WebSocket):
    await websocket.accept()
    try:
        session = await run_in_threadpool(SignSession)
    except Exception as exc:
        import traceback
        print(f"[ws_infer] ERROR creating SignSession: {exc}")
        traceback.print_exc()
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close()
        return
    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "frame":
                frame = await run_in_threadpool(decode_frame, msg["data"])
                result = await run_in_threadpool(session.process_frame, frame)
                await websocket.send_json(result)

                if result["should_flush"]:
                    await _flush_and_send(websocket, session)

            elif msg_type == "flush":
                await _flush_and_send(websocket, session)

            elif msg_type == "clear":
                session.clear()
                await websocket.send_json({"type": "cleared"})

    except WebSocketDisconnect:
        pass
    finally:
        session.close()


async def _flush_and_send(websocket: WebSocket, session: SignSession):
    result = await run_in_threadpool(session.flush_sync)
    if result["sentence"]:
        audio_bytes, mime = await run_in_threadpool(tts_service.synthesize, result["sentence"])
        result["audio"] = base64.b64encode(audio_bytes).decode("ascii")
        result["audio_mime"] = mime
    await websocket.send_json(result)


# ── WebSocket: data collection ───────────────────────────────────────────

@app.websocket("/ws/collect")
async def ws_collect(websocket: WebSocket):
    await websocket.accept()
    try:
        session = await run_in_threadpool(CollectSession)
    except Exception as exc:
        import traceback
        print(f"[ws_collect] ERROR creating CollectSession: {exc}")
        traceback.print_exc()
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close()
        return
    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "start_sequence":
                seq_idx = await run_in_threadpool(session.start_sequence, msg["word"])
                await websocket.send_json({"type": "sequence_started", "index": seq_idx})

            elif msg_type == "frame":
                frame = await run_in_threadpool(decode_frame, msg["data"])
                result = await run_in_threadpool(session.add_frame, frame)
                await websocket.send_json(result)

    except WebSocketDisconnect:
        pass
    finally:
        session.close()


@app.on_event("startup")
def preload_model():
    """Load the Keras model once at startup instead of on the first request."""
    try:
        ModelRegistry.get()
        print("[startup] Model loaded.")
    except FileNotFoundError as e:
        print(f"[startup] WARNING: {e}")
