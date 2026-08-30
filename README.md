# 🤟 Sign Language to Speech — Full-Stack

Real-time sign language recognition, translated into natural-language speech —
now as a full-stack web app. A browser captures the webcam feed; a FastAPI
backend runs MediaPipe hand/face tracking, an LSTM gesture classifier, a
LangChain + Ollama LLM to turn gesture tokens into sentences, and TTS
synthesis — all streamed live over WebSockets.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TensorFlow](https://img.shields.io/badge/TensorFlow-Keras_LSTM-FF6F00?logo=tensorflow&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Hand_%26_Face-00A98F)
![LangChain](https://img.shields.io/badge/LangChain-Ollama-1C3C3C)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## ✨ Features

- **Live gesture recognition** — 21-class hand gesture classifier (stacked LSTM over MediaPipe landmarks), streamed frame-by-frame from the browser
- **Sentence generation** — LangChain + a locally-hosted Ollama model turns raw gesture tokens into coherent, natural-language sentences
- **Emotion-aware output** — facial landmark heuristics (with optional DeepFace backend) feed emotion context into the LLM prompt
- **Speech output** — server-synthesized audio (pyttsx3 / gTTS) streamed back and played in-browser
- **Browser-based data collection** — record new gesture classes straight from the webcam, no local scripts required
- **Zero desktop dependency** — replaces the original PyQt5 app entirely with a React UI

## 🏗️ Architecture

```
┌─────────────┐   webcam frames (WS)   ┌────────────────────────┐
│   Browser    │ ─────────────────────▶ │   FastAPI Backend       │
│   (React)    │ ◀───────────────────── │   /ws/infer  /ws/collect│
└─────────────┘   tokens + sentence     │                          │
                    + audio (WS)         │  MediaPipe → LSTM        │
                                          │  → LangChain/Ollama      │
                                          │  → TTS synthesis         │
                                          └────────────────────────┘
```

| Layer | Tech |
|---|---|
| Frontend | React + Vite, `getUserMedia`, WebSocket hooks |
| API / real-time | FastAPI, WebSockets |
| Computer vision | MediaPipe Hand & Face Landmarker (Tasks API) |
| Gesture classification | TensorFlow/Keras — stacked LSTM |
| Language generation | LangChain + Ollama (local LLM) |
| Speech synthesis | pyttsx3 (offline) / gTTS (fallback) |

## 📁 Project structure

```
backend/
  app/
    main.py                 # FastAPI app — WS + REST endpoints
    services/
      inference_service.py  # live gesture → token pipeline
      collect_service.py    # browser-driven dataset recording
      emotion_detector.py   # facial landmark heuristics
      llm_interpreter.py    # LangChain + Ollama sentence generation
      tts_service.py        # text → audio bytes
  models/                    # trained sign_model.keras + model_meta.json
  dataset/ · processed/      # training data (generated)
  preprocess.py               # dataset → train/test arrays
  training_notebook.ipynb    # LSTM training

frontend/
  src/
    components/LivePage.jsx     # live translation UI
    components/CollectPage.jsx  # in-browser data collection UI
    hooks/useWebcam.js          # webcam capture + frame streaming
    hooks/useInferenceSocket.js # /ws/infer client
```

## 🚀 Getting started

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

> Ollama must be running locally (`ollama serve`) for sentence generation —
> it falls back to rule-based construction otherwise.

## 🧠 Training your own gestures

1. Open the **Collect Data** tab and record sequences for each new word (saved to `backend/dataset/`)
2. `python preprocess.py` → builds `processed/`
3. Run `training_notebook.ipynb` → produces `models/sign_model.keras` + `models/model_meta.json`
4. Restart the backend to load the new model

## 📄 License

MIT
