"""
Core inference pipeline, ported from the original gui.py (VideoThread).
Difference from the desktop version: frames arrive one at a time from the
browser over a WebSocket instead of being pulled from a local cv2.VideoCapture
loop, so state (buffers, timers, token history) lives on a per-connection
SignSession object instead of a QThread.
"""

import json
import os
import threading
import time
from collections import deque

from dotenv import load_dotenv
load_dotenv()

import cv2
import numpy as np
import mediapipe as mp
import tensorflow as tf
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from .emotion_detector import EmotionDetector
from .llm_interpreter import LLMInterpreter

SEQUENCE_LENGTH = 30
CONFIDENCE_THRESH = 0.70
SAME_WORD_STREAK = 8
PAUSE_SECONDS = 2.5
MAX_TOKEN_BUFFER = 20

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HAND_MODEL_PATH = os.path.join(BASE_DIR, "hand_landmarker.task")
MODEL_PATH = os.path.join(BASE_DIR, "models", "sign_model.keras")
META_PATH = os.path.join(BASE_DIR, "models", "model_meta.json")

_model_lock = threading.Lock()


def extract_landmarks(result) -> np.ndarray:
    """Same 126-dim two-hand vector extraction as collect_data.py / gui.py."""
    lh = np.zeros(63, dtype=np.float32)
    rh = np.zeros(63, dtype=np.float32)
    if result.hand_landmarks:
        for idx, hand_info in enumerate(result.handedness):
            label = hand_info[0].category_name
            lms = result.hand_landmarks[idx]
            base_x, base_y, base_z = lms[0].x, lms[0].y, lms[0].z
            coords = []
            for lm in lms:
                coords.append(lm.x - base_x)
                coords.append(lm.y - base_y)
                coords.append(lm.z - base_z)
            coords_array = np.array(coords, dtype=np.float32)
            if label == "Left":
                if np.all(lh == 0):
                    lh = coords_array
                else:
                    rh = coords_array
            else:
                if np.all(rh == 0):
                    rh = coords_array
                else:
                    lh = coords_array
    return np.concatenate([lh, rh])


def normalize(seq: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(seq, axis=-1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    return seq / norms


class ModelRegistry:
    """Loads the Keras model + label map once; shared (read-only) across sessions."""

    _model = None
    _label_map = None

    @classmethod
    def get(cls):
        if cls._model is None:
            if not os.path.exists(MODEL_PATH):
                raise FileNotFoundError(
                    f"Model not found at {MODEL_PATH}. Train it via training_notebook.ipynb first."
                )
            cls._model = tf.keras.models.load_model(MODEL_PATH)
            with open(META_PATH) as f:
                meta = json.load(f)
            cls._label_map = {int(k): v for k, v in meta["label_map"].items()}
        return cls._model, cls._label_map


class SignSession:
    """Per-WebSocket-connection state. One instance per connected client."""

    def __init__(self, llm_model: str = os.environ.get("GEMINI_MODEL", "gemini-3.7-flash")):
        self.model, self.label_map = ModelRegistry.get()

        base_options = python.BaseOptions(model_asset_path=HAND_MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options, num_hands=2,
            min_hand_detection_confidence=0.7, min_tracking_confidence=0.5,
        )
        self.hand_detector = vision.HandLandmarker.create_from_options(options)
        self.emotion_detector = EmotionDetector(smoothing=12)
        self.llm = LLMInterpreter(model=llm_model)

        self.frame_buffer: deque = deque(maxlen=SEQUENCE_LENGTH)
        self.token_buffer: list[str] = []
        self.history: list[str] = []
        self.last_word = None
        self.same_word_count = 0
        self.last_hand_time = time.time()
        self.llm_pending = False

    def process_frame(self, bgr_frame: np.ndarray) -> dict:
        """Run one frame through the pipeline. Returns a status dict to send to the client."""
        emotion = self.emotion_detector.update(bgr_frame)

        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.hand_detector.detect(mp_img)

        hand_detected = bool(result.hand_landmarks)
        if hand_detected:
            self.last_hand_time = time.time()

        landmarks = extract_landmarks(result)
        self.frame_buffer.append(landmarks)

        confidence = 0.0
        new_word = None

        if len(self.frame_buffer) == SEQUENCE_LENGTH and hand_detected:
            seq = normalize(np.array(list(self.frame_buffer), dtype=np.float32))
            inp = np.expand_dims(seq, 0)
            with _model_lock:
                probs = self.model.predict(inp, verbose=0)[0]
            idx = int(np.argmax(probs))
            confidence = float(probs[idx])

            if confidence >= CONFIDENCE_THRESH:
                word = self.label_map[idx]
                if word == self.last_word:
                    self.same_word_count += 1
                else:
                    self.last_word = word
                    self.same_word_count = 1

                if self.same_word_count == SAME_WORD_STREAK:
                    self.token_buffer.append(word)
                    new_word = word
                    if len(self.token_buffer) >= MAX_TOKEN_BUFFER:
                        self.ready_to_flush = True

        should_flush = (
            self.token_buffer
            and not self.llm_pending
            and (time.time() - self.last_hand_time) > PAUSE_SECONDS
        )

        return {
            "type": "frame_result",
            "emotion": emotion,
            "confidence": confidence,
            "hand_detected": hand_detected,
            "new_word": new_word,
            "tokens": list(self.token_buffer),
            "should_flush": should_flush,
        }

    def flush_sync(self) -> dict:
        """Blocking call to the LLM. Run via run_in_threadpool from the WS handler."""
        if not self.token_buffer:
            return {"type": "sentence", "sentence": "", "tokens": []}
        self.llm_pending = True
        try:
            emotion = self.emotion_detector.emotion
            sentence = self.llm.interpret(list(self.token_buffer), emotion)
        finally:
            self.llm_pending = False
        flushed_tokens = list(self.token_buffer)
        self.token_buffer.clear()
        if sentence:
            self.history.insert(0, sentence)
            self.history = self.history[:5]
        return {
            "type": "sentence",
            "sentence": sentence,
            "tokens": flushed_tokens,
            "history": self.history,
        }

    def clear(self):
        self.token_buffer.clear()
        self.frame_buffer.clear()
        self.last_word = None
        self.same_word_count = 0

    def close(self):
        self.hand_detector.close()
        self.emotion_detector.close()
