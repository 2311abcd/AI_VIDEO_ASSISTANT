# 🎬 VidMind — AI Video Assistant

> **Watch less. Know more.**
> Turn any YouTube video or recording into a transcript, summary, action items, key decisions and open questions, then chat with the video.

VidMind is a Streamlit web app that listens to a video or audio file for you. Paste a YouTube link or upload a recording, and it produces a structured report and a chatbot that answers questions grounded in the transcript.

**LIVE_DEMO_LINK** :https://aivideoassistant-vcoxgr9tgx6jnoiyhp6afa.streamlit.app/
📊 **Project presentation:** [VidMind_Presentation.pptx](docs/VidMind_Presentation.pptx)

---

## ✨ Features

| Feature | What it does |
|---|---|
| **Transcription** | Converts speech to text from a YouTube link or an uploaded file (mp4, mkv, mov, webm, mp3, wav, m4a) |
| **English + Hinglish** | English uses OpenAI Whisper locally. Hinglish uses Sarvam AI, which transcribes and translates to English |
| **Smart summary** | Long transcripts are summarized chunk by chunk, then combined into one bullet-point summary |
| **Extraction** | Action items (task, owner, deadline), key decisions, and open questions |
| **Chat with the video** | Ask follow-up questions; answers come only from the transcript (RAG) |
| **Transcript search** | Highlights any word you type inside the transcript |
| **Downloads** | Full report (`.md`) and transcript (`.txt`) |

---

## 🧠 How it works

```
YouTube URL / uploaded file
        │
        ▼
 1. Audio preparation      yt-dlp + ffmpeg + pydub
    (download → WAV 16 kHz mono → 10-minute chunks)
        │
        ▼
 2. Transcription          English  → Whisper (local)
                           Hinglish → Sarvam AI (speech-to-text-translate)
        │
        ▼
 3. Understanding          Mistral LLM via LangChain
    • title (max 8 words)
    • map-reduce summary
    • action items / decisions / open questions
        │
        ▼
 4. Indexing for chat      Split transcript → embeddings (all-MiniLM-L6-v2)
                           → ChromaDB vector store
        │
        ▼
 5. Chat (RAG)             Question → top-4 relevant chunks → LLM answers
                           using only that context
```

### Why RAG for chat?
Instead of sending the whole transcript to the model for every question, the app retrieves only the 4 most relevant 500-character chunks. This keeps answers fast, cheap and grounded. If the answer isn't in the video, the assistant says so instead of guessing.

---

## 🛠️ Tech stack

- **UI:** Streamlit (custom dark glassmorphism theme)
- **Audio:** yt-dlp, ffmpeg, pydub
- **Speech-to-text:** OpenAI Whisper (English), Sarvam AI (Hinglish)
- **LLM:** Mistral AI (`codestral-2508`) through LangChain
- **Embeddings and vector DB:** sentence-transformers (`all-MiniLM-L6-v2`) and ChromaDB

---

## 📁 Project structure

```
.
├── app.py                  # Streamlit app (UI + pipeline with live progress)
├── main.py                 # Command-line version of the same pipeline
├── core/
│   ├── transcriber.py      # Whisper / Sarvam transcription
│   ├── summarizer.py       # Title + map-reduce summary
│   ├── extractor.py        # Action items, decisions, open questions
│   ├── rag_engine.py       # RAG chain and ask_question()
│   └── vector_store.py     # ChromaDB + embeddings
├── utils/
│   └── audio_processor.py  # Download, convert and chunk audio
├── docs/
│   └── VidMind_Presentation.pptx
├── requirements.txt
├── packages.txt            # System packages (ffmpeg) for Streamlit Cloud
└── README.md
```

---

## 🚀 Run locally

### 1. Prerequisites
- Python 3.11 (recommended)
- [ffmpeg](https://ffmpeg.org/download.html) installed (`brew install ffmpeg` on macOS, `sudo apt install ffmpeg` on Ubuntu)

### 2. Clone and install
```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add your API keys
Create a `.env` file in the project root:
```env
MISTRAL_API_KEY=your_mistral_key
SARVAM_API_KEY=your_sarvam_key     # only needed for Hinglish
WHISPER_MODEL=small                # tiny / base / small / medium
```

### 4. Start the app
```bash
streamlit run app.py
```
Open the link shown in the terminal (usually http://localhost:8501).

### Or use the command line
```bash
python main.py
```

---

## ☁️ Deploy on Streamlit Community Cloud

1. Push this repo to GitHub (make sure `.env` is **not** committed).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **Create app**, then choose your repo, branch `main` and main file `app.py`.
3. In **Advanced settings**, choose **Python 3.11** and add your secrets:
   ```toml
   MISTRAL_API_KEY = "your_mistral_key"
   SARVAM_API_KEY = "your_sarvam_key"
   WHISPER_MODEL = "base"
   ```
4. Click **Deploy**. `packages.txt` installs ffmpeg automatically.

---

## ⚠️ Known limitations

- **YouTube on cloud hosting:** YouTube often blocks data-center IPs, so YouTube links may fail on a deployed app. File upload always works. Running locally avoids this. Optionally, a `YT_COOKIES` secret (exported `cookies.txt`) can help.
- **Memory:** Free hosting has limited RAM, so the `base` Whisper model is recommended there. Very long videos may be slow.
- **Shared vector store:** All analyses write to one ChromaDB collection, so chat may mix content when several videos are analyzed in a row.

---

## 🔮 Future improvements

- Per-session vector stores so each video has its own isolated chat
- Speaker diarization (who said what)
- Timestamps linked to the summary and chat answers
- Export to PDF
- More languages

---

## 📄 License

Add a license of your choice (for example MIT) before sharing publicly.
