"""
LLM Integration Module
Uses the native google-genai SDK with Google Gemini to convert
raw gesture tokens + emotion into a natural, grammatically-correct sentence.

Set the GOOGLE_API_KEY environment variable to your Gemini API key.
If no key is set, the interpreter falls back to a rule-based heuristic.
"""

import logging
import os
import threading
from typing import Callable, Optional

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "You are a sign language interpreter assistant. "
    "Convert sign language gesture tokens into a single, natural English sentence. "
    "Fix grammar and word order. Maintain the original meaning. "
    "Reflect the emotion subtly in tone if appropriate. "
    "Return ONLY the final sentence — no explanations, no quotes, no extra punctuation."
)

def _build_user_prompt(tokens: list[str], emotion: str) -> str:
    return f"Words: {' '.join(tokens)}\nEmotion: {emotion}\n\nSentence:"


class LLMInterpreter:
    """Wraps Google Gemini (google-genai SDK) for async sentence interpretation.

    Usage:
        llm = LLMInterpreter()
        # Sync:
        sentence = llm.interpret(["hello", "how", "you"], "happy")
        # Async (non-blocking):
        llm.interpret_async(["hello", "how", "you"],
                            emotion="happy",
                            callback=lambda s: print(s))
    """

    def __init__(self,
                 model: str = "gemini-3.7-flash",
                 api_key: Optional[str] = None,
                 timeout: int = 30):
        """
        Args:
            model:   Gemini model name (default: "gemini-3.7-flash").
            api_key: Google API key. Falls back to the GOOGLE_API_KEY env var.
            timeout: Request timeout in seconds.
        """
        self._model_name = model
        self._timeout = timeout
        self._lock = threading.Lock()
        self._busy = False
        self._client = None

        resolved_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        if not resolved_key:
            logger.warning(
                "[LLMInterpreter] GOOGLE_API_KEY is not set. "
                "Using fallback rule-based interpreter."
            )
            return

        try:
            from google import genai
            self._client = genai.Client(api_key=resolved_key)
            print(f"[LLMInterpreter] Connected to Gemini model '{model}'.")
        except Exception as e:
            logger.warning(
                "[LLMInterpreter] Could not initialise Gemini (%s). "
                "Using fallback rule-based interpreter.", e
            )

    # ── Public API ────────────────────────────────────────────────────────────

    def interpret(self, tokens: list[str], emotion: str = "neutral") -> str:
        """Synchronously convert tokens → sentence. Blocks until done."""
        if not tokens:
            return ""

        if self._client is None:
            return self._fallback(tokens, emotion)

        try:
            from google import genai
            from google.genai import types

            chat = self._client.chats.create(
                model=self._model_name,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                ),
            )
            response = chat.send_message(_build_user_prompt(tokens, emotion))
            sentence = response.text.strip().strip('"').strip("'")
            return sentence if sentence else self._fallback(tokens, emotion)

        except Exception as e:
            print(f"[LLMInterpreter] Inference error: {e}")
            return self._fallback(tokens, emotion)

    def interpret_async(self,
                        tokens: list[str],
                        emotion: str = "neutral",
                        callback: Optional[Callable[[str], None]] = None):
        """Non-blocking interpretation. Result delivered via callback."""
        if self._busy:
            return

        def _run():
            with self._lock:
                self._busy = True
            try:
                sentence = self.interpret(tokens, emotion)
            finally:
                self._busy = False
            if callback:
                callback(sentence)

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    @property
    def is_busy(self) -> bool:
        return self._busy

    # ── Fallback ──────────────────────────────────────────────────────────────

    @staticmethod
    def _fallback(tokens: list[str], emotion: str) -> str:
        """Simple heuristic when the Gemini API is unavailable."""
        sentence = " ".join(tokens).strip()
        if not sentence:
            return ""
        sentence = sentence[0].upper() + sentence[1:]
        if not sentence.endswith((".", "?", "!")):
            punctuation = "!" if emotion == "happy" else "."
            sentence += punctuation
        return sentence
