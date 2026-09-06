"""
Server-side Text-to-Speech.
Synthesizes a sentence into WAV/MP3 bytes so the browser can play it
via an <audio> element — replaces gui.py's direct pyttsx3.speak() call,
which only made sound on the machine running the desktop app.
"""

import io
import os
import tempfile

try:
    import pyttsx3
    _PYTTSX3_OK = True
except ImportError:
    _PYTTSX3_OK = False

try:
    from gtts import gTTS
    _GTTS_OK = True
except ImportError:
    _GTTS_OK = False


class TTSService:
    """Synchronous, stateless synthesizer. Call from a threadpool in async code."""

    def __init__(self, rate: int = 175, volume: float = 0.9, voice_index: int = 0):
        self._rate = rate
        self._volume = volume
        self._voice_index = voice_index
        # Prefer gTTS (works on any Linux server, including Render).
        # Fall back to pyttsx3 only when running locally on a machine with an
        # audio driver (Windows/macOS), and gTTS is not installed.
        if _GTTS_OK:
            self.backend = "gtts"
        elif _PYTTSX3_OK:
            self.backend = "pyttsx3"
        else:
            self.backend = None
            print("[TTSService] WARNING: no TTS backend available.")


    def synthesize(self, text: str) -> tuple[bytes, str]:
        """Returns (audio_bytes, mime_type). Raises on failure."""
        text = (text or "").strip()
        if not text:
            return b"", "audio/wav"

        if self.backend == "pyttsx3":
            return self._synth_pyttsx3(text), "audio/wav"
        elif self.backend == "gtts":
            return self._synth_gtts(text), "audio/mpeg"
        else:
            raise RuntimeError("No TTS backend installed (pip install pyttsx3 or gTTS)")

    def _synth_pyttsx3(self, text: str) -> bytes:
        engine = pyttsx3.init()
        engine.setProperty("rate", self._rate)
        engine.setProperty("volume", self._volume)
        voices = engine.getProperty("voices")
        if voices and self._voice_index < len(voices):
            engine.setProperty("voice", voices[self._voice_index].id)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fp:
            tmp_path = fp.name
        try:
            engine.save_to_file(text, tmp_path)
            engine.runAndWait()
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            os.unlink(tmp_path)

    def _synth_gtts(self, text: str) -> bytes:
        buf = io.BytesIO()
        gTTS(text=text, lang="en", slow=False).write_to_fp(buf)
        return buf.getvalue()
