"""
Browser-driven data collection, replacing collect_data.py's cv2.VideoCapture
loop. The frontend captures webcam frames and streams them over the
/ws/collect WebSocket; this module extracts landmarks and writes them to
dataset/<word>/<sequence>/<frame>.npy in the exact same layout preprocess.py
already expects, so nothing downstream changes.
"""

import os

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from .inference_service import HAND_MODEL_PATH, extract_landmarks

SEQUENCE_LENGTH = 30
DATASET_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "dataset",
)


class CollectSession:
    """One instance per /ws/collect connection. Records one word at a time."""

    def __init__(self):
        base_options = python.BaseOptions(model_asset_path=HAND_MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options, num_hands=2,
            min_hand_detection_confidence=0.7, min_tracking_confidence=0.5,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self.word = None
        self.seq_dir = None
        self.frame_idx = 0

    def start_sequence(self, word: str) -> int:
        """Creates the next sequence folder for `word`, returns its index."""
        word_dir = os.path.join(DATASET_DIR, word)
        os.makedirs(word_dir, exist_ok=True)
        existing = [int(f) for f in os.listdir(word_dir) if f.isdigit()]
        seq_idx = max(existing) + 1 if existing else 0
        self.seq_dir = os.path.join(word_dir, str(seq_idx))
        os.makedirs(self.seq_dir, exist_ok=True)
        self.word = word
        self.frame_idx = 0
        return seq_idx

    def add_frame(self, bgr_frame: np.ndarray) -> dict:
        """Extracts landmarks from one frame and saves it. Returns progress."""
        if self.seq_dir is None:
            raise RuntimeError("start_sequence() must be called first")

        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.detector.detect(mp_img)
        landmarks = extract_landmarks(result)

        np.save(os.path.join(self.seq_dir, str(self.frame_idx)), landmarks)
        self.frame_idx += 1

        done = self.frame_idx >= SEQUENCE_LENGTH
        return {
            "type": "collect_progress",
            "word": self.word,
            "frame": self.frame_idx,
            "total": SEQUENCE_LENGTH,
            "hand_detected": bool(result.hand_landmarks),
            "sequence_done": done,
        }

    def close(self):
        self.detector.close()
