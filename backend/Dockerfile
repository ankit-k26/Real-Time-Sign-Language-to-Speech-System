FROM python:3.10-slim

# ── System libraries required by MediaPipe Tasks API ────────────────────────
# MediaPipe's C++ shared lib needs libGLESv2.so.2 even in CPU-only/headless mode.
# OpenCV-headless also needs libGL and GLib.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgles2-mesa \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ─────────────────────────────────────────────────────────
COPY . .

# Render sets $PORT at runtime; default to 10000 for local Docker testing.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}
