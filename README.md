# 🤟 Sign Language to Speech — Full-Stack

Real-time sign language recognition, translated into natural-language speech —
as a full-stack web app. A browser captures the webcam feed; a FastAPI backend
runs MediaPipe hand/face tracking, an LSTM gesture classifier, Google Gemini
(via the native `google-genai` SDK) to turn gesture tokens into natural sentences,
and TTS synthesis — all streamed live over WebSockets.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TensorFlow](https://img.shields.io/badge/TensorFlow-Keras_LSTM-FF6F00?logo=tensorflow&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Hand_%26_Face-00A98F)
![Gemini](https://img.shields.io/badge/Google_Gemini-3.7_Flash-4285F4?logo=google&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## ✨ Features

- **Live gesture recognition** — hand gesture classifier (stacked LSTM over MediaPipe landmarks), streamed frame-by-frame from the browser
- **Sentence generation** — Google Gemini (`gemini-3.7-flash`) turns raw gesture tokens into coherent, natural-language sentences via the native `google-genai` SDK
- **Emotion-aware output** — facial landmark heuristics feed emotion context into the Gemini prompt for tone-aware responses
- **Speech output** — server-synthesized audio (pyttsx3 / gTTS) streamed back and played in-browser
- **Browser-based data collection** — record new gesture classes straight from the webcam, no local scripts required
- **Zero desktop dependency** — replaces the original PyQt5 app entirely with a React UI

## 🏗️ Architecture

```
┌─────────────┐   webcam frames (WS)   ┌──────────────────────────┐
│   Browser    │ ─────────────────────▶ │   FastAPI Backend          │
│   (React)    │ ◀───────────────────── │   /ws/infer  /ws/collect   │
└─────────────┘   tokens + sentence     │                             │
                    + audio (WS)         │  MediaPipe → LSTM           │
                                          │  → Gemini 3.7 Flash (LLM)  │
                                          │  → TTS synthesis            │
                                          └──────────────────────────┘
```

| Layer | Tech |
|---|---|
| Frontend | React 18 + Vite, `getUserMedia`, WebSocket hooks |
| API / real-time | FastAPI, WebSockets |
| Computer vision | MediaPipe Hand & Face Landmarker (Tasks API) |
| Gesture classification | TensorFlow/Keras — stacked LSTM |
| Language generation | Google Gemini `gemini-3.7-flash` via `google-genai` SDK |
| Speech synthesis | pyttsx3 (offline) / gTTS (online fallback) |

## 📁 Project structure

```
backend/
  .env                        # your API keys & config (git-ignored)
  .env.example                # safe template — copy to .env
  app/
    main.py                   # FastAPI app — WS + REST endpoints
    services/
      inference_service.py    # live gesture → token pipeline
      collect_service.py      # browser-driven dataset recording
      emotion_detector.py     # facial landmark heuristics
      llm_interpreter.py      # Gemini sentence generation (google-genai)
      tts_service.py          # text → audio bytes
  models/                     # trained sign_model.keras + model_meta.json
  dataset/ · processed/       # training data (generated locally)
  preprocess.py               # dataset → train/test arrays
  training_notebook.ipynb     # LSTM training

frontend/
  .env                        # frontend env vars (git-ignored)
  .env.example                # safe template — copy to .env
  src/
    components/LivePage.jsx     # live translation UI
    components/CollectPage.jsx  # in-browser data collection UI
    hooks/useWebcam.js          # webcam capture + frame streaming
    hooks/useInferenceSocket.js # /ws/infer client
```

## 🚀 Getting started

### 1. Clone & set up environment variables

```bash
# Backend
cp backend/.env.example backend/.env
# Then open backend/.env and fill in your GOOGLE_API_KEY
```

Get a free Gemini API key at **https://aistudio.google.com/app/apikey**

```bash
# Frontend (optional — defaults work for local dev)
cp frontend/.env.example frontend/.env
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

> If `GOOGLE_API_KEY` is not set, sentence generation falls back to a
> simple rule-based constructor so the app still works without an API key.

## ⚙️ Key environment variables (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_API_KEY` | *(required)* | Gemini API key from Google AI Studio |
| `GEMINI_MODEL` | `gemini-3.7-flash` | Gemini model for sentence generation |
| `TTS_BACKEND` | `pyttsx3` | `pyttsx3` (offline) or `gtts` (online) |
| `CONFIDENCE_THRESH` | `0.70` | Minimum gesture confidence to accept |
| `PAUSE_SECONDS` | `2.5` | Silence duration to trigger auto-flush |
| `ALLOWED_ORIGINS` | `*` | CORS origins (tighten in production) |

## 🧠 Training your own gestures

1. Open the **Collect Data** tab and record sequences for each new word (saved to `backend/dataset/`)
2. `python preprocess.py` → builds `processed/`
3. Run `training_notebook.ipynb` → produces `models/sign_model.keras` + `models/model_meta.json`
4. Restart the backend to load the new model

## 📄 License

MIT
