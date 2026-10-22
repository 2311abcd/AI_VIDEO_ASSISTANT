try:
    __import__("pysqlite3")
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass
from dotenv import load_dotenv
load_dotenv()  # sabse pehle

import html
import os
import re
import tempfile

import streamlit as st

from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import (
    extract_action_items,
    extract_key_decisions,
    extract_questions,
)
from core.rag_engine import build_rag_chain, ask_question

# ----------------------------------------------------------------------------
# Page setup
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="VidMind - AI Video Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');

:root {
  --bg: #080B16;
  --panel: rgba(255,255,255,.045);
  --panel-hi: rgba(255,255,255,.08);
  --line: rgba(255,255,255,.10);
  --text: #E8ECF8;
  --muted: #8D96B3;
  --indigo: #6D5BFF;
  --pink: #FF4D8D;
  --orange: #FF9B54;
  --cyan: #3DD6F5;
  --amber: #FFC857;
  --green: #4ADE9A;
  --grad: linear-gradient(120deg, #6D5BFF 0%, #FF4D8D 55%, #FF9B54 100%);
}

/* ---------- base ---------- */
html, body, .stApp, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--text); }
h1, h2, h3, h4 { font-family: 'Sora', sans-serif !important; letter-spacing: -0.02em; }
.stApp { background: var(--bg); }

/* the one ambient moment: slow drifting colour glow + faint grid */
.stApp::before {
  content: ""; position: fixed; inset: -20%; z-index: 0; pointer-events: none;
  background:
    radial-gradient(38% 38% at 18% 14%, rgba(109,91,255,.32), transparent 70%),
    radial-gradient(34% 34% at 88% 82%, rgba(255,77,141,.20), transparent 70%),
    radial-gradient(26% 26% at 70% 10%, rgba(61,214,245,.10), transparent 70%);
  animation: drift 28s ease-in-out infinite alternate;
}
.stApp::after {
  content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image:
    linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
  background-size: 44px 44px;
  -webkit-mask-image: radial-gradient(ellipse at 50% 0%, #000 20%, transparent 75%);
          mask-image: radial-gradient(ellipse at 50% 0%, #000 20%, transparent 75%);
}
@keyframes drift { from { transform: translate3d(-2%, -1%, 0) scale(1); }
                   to   { transform: translate3d(3%, 2%, 0) scale(1.08); } }
@media (prefers-reduced-motion: reduce) { .stApp::before { animation: none; } }

[data-testid="stAppViewContainer"], section[data-testid="stSidebar"] { position: relative; z-index: 1; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], [data-testid="stDeployButton"], #MainMenu, footer { display: none !important; }
.block-container { max-width: 1180px; padding: 2.4rem 2rem 5rem; }

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,.14); border-radius: 10px; }
::-webkit-scrollbar-track { background: transparent; }

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] {
  background: rgba(10,14,30,.72); backdrop-filter: blur(18px);
  border-right: 1px solid var(--line);
}
section[data-testid="stSidebar"] .block-container, section[data-testid="stSidebar"] > div { padding-top: 1.6rem; }
.brand { display: flex; align-items: center; gap: .75rem; margin-bottom: .4rem; }
.brand-logo {
  width: 42px; height: 42px; border-radius: 13px; background: var(--grad);
  display: grid; place-items: center; color: #fff; font-size: 1.05rem;
  box-shadow: 0 8px 28px rgba(255,77,141,.35);
}
.brand-name { font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.25rem; line-height: 1.1; }
.brand-sub { color: var(--muted); font-size: .8rem; }
.side-rule { height: 1px; background: var(--line); margin: 1.1rem 0 1.2rem; }

/* ---------- inputs ---------- */
label, [data-testid="stWidgetLabel"] p { color: var(--muted) !important; font-weight: 500; font-size: .85rem; }
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
  background: rgba(255,255,255,.05) !important; border: 1px solid var(--line) !important;
  border-radius: 12px !important; transition: border-color .15s, box-shadow .15s;
}
div[data-baseweb="input"] > div:focus-within, div[data-baseweb="select"] > div:focus-within {
  border-color: var(--indigo) !important; box-shadow: 0 0 0 3px rgba(109,91,255,.25);
}
input, textarea { color: var(--text) !important; }
section[data-testid="stFileUploaderDropzone"] {
  background: rgba(255,255,255,.035); border: 1.5px dashed rgba(255,255,255,.22); border-radius: 14px;
}
section[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--pink); background: rgba(255,77,141,.06); }

/* ---------- buttons ---------- */
.stButton > button, .stDownloadButton > button {
  border-radius: 12px; border: 1px solid var(--line); background: var(--panel);
  color: var(--text); font-weight: 600; padding: .6rem 1rem; transition: all .18s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  border-color: rgba(255,255,255,.3); background: var(--panel-hi); transform: translateY(-1px);
}
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {
  background: var(--grad); border: none; color: #fff;
  box-shadow: 0 10px 30px rgba(255,77,141,.30);
}
.stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
  box-shadow: 0 14px 38px rgba(255,77,141,.5); transform: translateY(-2px); filter: brightness(1.08);
}

/* ---------- radio as segmented control ---------- */
div[role="radiogroup"] { gap: .4rem; }
div[role="radiogroup"] > label {
  background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: .35rem .8rem; cursor: pointer;
}
div[role="radiogroup"] > label:has(input:checked) { background: rgba(109,91,255,.2); border-color: var(--indigo); }
div[role="radiogroup"] > label > div:first-child { display: none; }

/* ---------- tabs as pills ---------- */
div[data-baseweb="tab-list"] {
  gap: .4rem; background: var(--panel); border: 1px solid var(--line);
  padding: .35rem; border-radius: 16px; overflow-x: auto;
}
button[data-baseweb="tab"] {
  height: auto; padding: .55rem 1rem; border-radius: 11px; color: var(--muted); font-weight: 600;
  background: transparent;
}
button[data-baseweb="tab"]:hover { color: var(--text); }
button[data-baseweb="tab"][aria-selected="true"] { color: #fff; background: rgba(109,91,255,.28); }
div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] { display: none; }
div[data-baseweb="tab-panel"] { padding-top: 1.4rem; }

/* ---------- hero ---------- */
.hero { padding: 3.2rem 0 1.2rem; }
.pill {
  display: inline-flex; align-items: center; gap: .55rem; padding: .38rem .9rem;
  border: 1px solid var(--line); background: var(--panel); border-radius: 999px;
  font-size: .82rem; color: var(--muted); margin-bottom: 1.4rem;
}
.pill .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 12px var(--green); }
.hero h1 {
  font-size: clamp(2.8rem, 7vw, 5.2rem); line-height: 1.02; font-weight: 800;
  margin: 0 0 1.2rem; letter-spacing: -0.04em;
}
.grad { background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
.hero p { color: var(--muted); font-size: 1.15rem; max-width: 36rem; line-height: 1.6; }
.hint { margin-top: 1.6rem; color: var(--muted); font-size: .92rem; }
.hint b { color: var(--text); }

.feat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 2.6rem; }
@media (max-width: 800px) { .feat-grid { grid-template-columns: 1fr; } }
.feat {
  background: var(--panel); border: 1px solid var(--line); border-radius: 20px; padding: 1.4rem;
  backdrop-filter: blur(10px); transition: transform .2s, border-color .2s;
}
.feat:hover { transform: translateY(-4px); border-color: rgba(255,255,255,.25); }
.feat .ic {
  width: 44px; height: 44px; border-radius: 13px; display: grid; place-items: center;
  font-size: 1.2rem; margin-bottom: 1rem;
}
.ic.a { background: rgba(109,91,255,.22); } .ic.b { background: rgba(255,200,87,.20); } .ic.c { background: rgba(255,77,141,.22); }
.feat h3 { font-size: 1.1rem; margin: 0 0 .35rem; }
.feat p { color: var(--muted); font-size: .95rem; margin: 0; line-height: 1.5; }

/* ---------- result header ---------- */
.r-tag {
  display: inline-block; font-size: .78rem; font-weight: 600; padding: .3rem .75rem; border-radius: 999px;
  color: var(--green); background: rgba(74,222,154,.12); border: 1px solid rgba(74,222,154,.3); margin-bottom: 1rem;
}
.r-title { font-family: 'Sora', sans-serif; font-weight: 800; font-size: clamp(1.9rem, 4vw, 3rem);
  line-height: 1.1; letter-spacing: -0.03em; margin: 0 0 .7rem; }
.r-src { color: var(--muted); font-size: .92rem; word-break: break-all; margin-bottom: 1.6rem; }

.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1.2rem; }
@media (max-width: 700px) { .stats { grid-template-columns: 1fr; } }
.stat { background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 1.1rem 1.3rem; }
.stat .n { font-family: 'Sora', sans-serif; font-size: 1.8rem; font-weight: 700; }
.stat .l { color: var(--muted); font-size: .85rem; }

/* ---------- content cards ---------- */
.glass {
  background: var(--panel); border: 1px solid var(--line); border-radius: 20px;
  padding: 1.6rem 1.8rem; backdrop-filter: blur(10px); line-height: 1.75; font-size: 1.02rem;
  position: relative; overflow: hidden;
}
.glass::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--grad); }
.glass p { margin: 0 0 .9rem; } .glass p:last-child { margin-bottom: 0; }
.glass ul { margin: 0 0 .9rem; padding-left: 1.2rem; } .glass li { margin-bottom: .35rem; }

.vcard {
  display: flex; gap: 1rem; align-items: flex-start; background: var(--panel);
  border: 1px solid var(--line); border-radius: 16px; padding: 1rem 1.2rem; margin-bottom: .75rem;
  line-height: 1.6; transition: transform .18s, border-color .18s, background .18s;
}
.vcard:hover { transform: translateX(4px); background: var(--panel-hi); }
.vcard .vi {
  flex: 0 0 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; font-size: .95rem;
}
.vcard.amber .vi { background: rgba(255,200,87,.18); } .vcard.amber:hover { border-color: rgba(255,200,87,.5); }
.vcard.green .vi { background: rgba(74,222,154,.16); } .vcard.green:hover { border-color: rgba(74,222,154,.5); }
.vcard.violet .vi { background: rgba(109,91,255,.22); } .vcard.violet:hover { border-color: rgba(109,91,255,.6); }
.vcard strong { color: #fff; }
.empty-card { text-align: center; color: var(--muted); padding: 2.4rem 1rem; border: 1px dashed var(--line); border-radius: 16px; }

.tbox {
  background: rgba(0,0,0,.35); border: 1px solid var(--line); border-radius: 16px; padding: 1.3rem 1.5rem;
  max-height: 460px; overflow-y: auto; line-height: 1.8; font-size: .97rem; color: #C9D0E6; margin: .8rem 0 1rem;
}
.tbox mark { background: rgba(255,200,87,.35); color: #fff; padding: 0 .15rem; border-radius: 4px; }

/* ---------- chat ---------- */
div[data-testid="stChatMessage"] {
  background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 1rem 1.2rem;
}
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
  background: linear-gradient(120deg, rgba(109,91,255,.30), rgba(255,77,141,.22)); border-color: rgba(255,255,255,.18);
}
div[data-testid="stChatInput"] { border-radius: 16px; border: 1px solid var(--line); background: rgba(255,255,255,.05); }
div[data-testid="stChatInput"]:focus-within { border-color: var(--indigo); box-shadow: 0 0 0 3px rgba(109,91,255,.25); }
div[data-testid="stChatInput"] textarea { color: var(--text) !important; }

/* ---------- status box ---------- */
div[data-testid="stStatus"], details[data-testid="stExpander"] {
  background: var(--panel); border: 1px solid var(--line); border-radius: 16px;
}
div[data-testid="stAlert"] { border-radius: 14px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Tiny HTML helpers
# ----------------------------------------------------------------------------
def H(s: str) -> str:
    """Collapse multi-line HTML to one line so Markdown never treats it as code."""
    return "".join(line.strip() for line in s.splitlines())


def inline(text: str) -> str:
    t = html.escape(str(text))
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


BULLET = re.compile(r"^\s*(?:[-*\u2022]|\d+[.)])\s+(.*)")


def to_items(content):
    """Normalise str/list output into [(kind, text)] where kind is 'item' or 'p'."""
    if not content:
        return []
    if isinstance(content, (list, tuple)):
        return [("item", str(c)) for c in content if str(c).strip()]
    out = []
    for line in str(content).splitlines():
        line = line.strip()
        if not line:
            continue
        m = BULLET.match(line)
        if m:
            out.append(("item", m.group(1)))
        else:
            out.append(("p", re.sub(r"^#{1,6}\s*", "", line)))
    return out


def render_summary(content):
    items = to_items(content)
    if not items:
        st.markdown(H('<div class="empty-card">No summary available.</div>'), unsafe_allow_html=True)
        return
    parts, in_ul = [], False
    for kind, text in items:
        if kind == "item":
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            parts.append(f"<li>{inline(text)}</li>")
        else:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(f"<p>{inline(text)}</p>")
    if in_ul:
        parts.append("</ul>")
    st.markdown(f'<div class="glass">{"".join(parts)}</div>', unsafe_allow_html=True)


def render_cards(content, icon, tone, empty_msg):
    items = to_items(content)
    if not items:
        st.markdown(f'<div class="empty-card">{empty_msg}</div>', unsafe_allow_html=True)
        return
    parts = []
    for _, text in items:
        parts.append(
            f'<div class="vcard {tone}"><div class="vi">{icon}</div><div>{inline(text)}</div></div>'
        )
    st.markdown("".join(parts), unsafe_allow_html=True)


def as_text(content) -> str:
    if isinstance(content, (list, tuple)):
        return "\n".join(f"- {c}" for c in content)
    return str(content or "")


def build_report(r: dict, source: str) -> str:
    return (
        f"# {r['title']}\n\nSource: {source}\n\n"
        f"## Summary\n{as_text(r['summary'])}\n\n"
        f"## Action items\n{as_text(r['action_items'])}\n\n"
        f"## Key decisions\n{as_text(r['key_decisions'])}\n\n"
        f"## Open questions\n{as_text(r['open_questions'])}\n"
    )


def transcript_html(text: str, query: str) -> str:
    safe = html.escape(text)
    if query.strip():
        pat = re.compile(re.escape(html.escape(query.strip())), re.IGNORECASE)
        safe = pat.sub(lambda m: f"<mark>{m.group(0)}</mark>", safe)
    return f'<div class="tbox">{safe.replace(chr(10), "<br>")}</div>'


# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
for key, default in {
    "result": None,
    "messages": [],
    "source_label": "",
    "language": "english",
    "pending_q": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def set_pending(q: str):
    st.session_state.pending_q = q


# ----------------------------------------------------------------------------
# Pipeline (same steps as run_pipeline, with live progress)
# ----------------------------------------------------------------------------
def analyze(source: str, language: str) -> dict:
    with st.status("Analyzing your video…", expanded=True) as status:
        try:
            st.write("🎧 Preparing audio…")
            chunks = process_input(source)

            st.write("📝 Transcribing…")
            transcript = transcribe_all(chunks, language)

            st.write("✨ Writing title and summary…")
            title = generate_title(transcript)
            summary = summarize(transcript)

            st.write("🔎 Finding action items, decisions and open questions…")
            action_items = extract_action_items(transcript)
            decisions = extract_key_decisions(transcript)
            questions = extract_questions(transcript)

            st.write("🧠 Indexing transcript for chat…")
            rag_chain = build_rag_chain(transcript)

            status.update(label="Analysis complete", state="complete", expanded=False)
        except Exception as e:
            status.update(label="Analysis failed", state="error", expanded=True)
            st.error(f"Something went wrong: {e}")
            st.stop()

    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_items,
        "key_decisions": decisions,
        "open_questions": questions,
        "rag_chain": rag_chain,
    }


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        H(
            """
            <div class="brand">
              <div class="brand-logo">▶</div>
              <div><div class="brand-name">VidMind</div><div class="brand-sub">AI video assistant</div></div>
            </div>
            <div class="side-rule"></div>
            """
        ),
        unsafe_allow_html=True,
    )

    input_mode = st.radio("Source", ["YouTube URL", "Upload file"], horizontal=True)

    url, uploaded = None, None
    if input_mode == "YouTube URL":
        url = st.text_input("YouTube link", placeholder="https://youtube.com/watch?v=…")
    else:
        uploaded = st.file_uploader(
            "Video or audio file",
            type=["mp4", "mkv", "mov", "webm", "mp3", "wav", "m4a"],
        )

    language = st.selectbox("Spoken language", ["english", "hinglish"])
    st.write("")
    analyze_clicked = st.button("Analyze video", type="primary", use_container_width=True)

    if st.session_state.result is not None:
        if st.button("Start over", use_container_width=True):
            st.session_state.result = None
            st.session_state.messages = []
            st.session_state.source_label = ""
            st.rerun()

# ----------------------------------------------------------------------------
# Run pipeline on click
# ----------------------------------------------------------------------------
if analyze_clicked:
    tmp_path, source, label = None, None, ""

    if input_mode == "YouTube URL":
        if not url or not url.strip():
            st.sidebar.error("Paste a YouTube link first.")
        else:
            source, label = url.strip(), url.strip()
    else:
        if uploaded is None:
            st.sidebar.error("Upload a file first.")
        else:
            suffix = os.path.splitext(uploaded.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.getbuffer())
                tmp_path = tmp.name
            source, label = tmp_path, uploaded.name

    if source:
        try:
            st.session_state.result = analyze(source, language)
            st.session_state.source_label = label
            st.session_state.language = language
            st.session_state.messages = []
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

# ----------------------------------------------------------------------------
# Main area
# ----------------------------------------------------------------------------
result = st.session_state.result

if result is None:
    st.markdown(
        H(
            """
            <div class="hero">
              <div class="pill"><span class="dot"></span>Supports English and Hinglish</div>
              <h1>Watch less.<br><span class="grad">Know more.</span></h1>
              <p>Drop in a YouTube link or a recording. Get the summary, action items and decisions,
              then ask the video anything.</p>
              <div class="hint">Paste a link in the sidebar and press <b>Analyze video</b>.</div>
              <div class="feat-grid">
                <div class="feat"><div class="ic a">🎧</div><h3>Transcribe</h3>
                  <p>Audio from any YouTube link or local file, turned into a clean transcript.</p></div>
                <div class="feat"><div class="ic b">⚡</div><h3>Extract</h3>
                  <p>Summary, action items, key decisions and open questions, ready to read.</p></div>
                <div class="feat"><div class="ic c">💬</div><h3>Chat</h3>
                  <p>Ask follow-up questions and get answers grounded in the transcript.</p></div>
              </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
else:
    words = len(result["transcript"].split())
    st.markdown(
        H(
            f"""
            <div class="r-tag">Analysis ready</div>
            <div class="r-title">{html.escape(str(result['title']))}</div>
            <div class="r-src">{html.escape(st.session_state.source_label)}</div>
            <div class="stats">
              <div class="stat"><div class="n">{words:,}</div><div class="l">words transcribed</div></div>
              <div class="stat"><div class="n">{max(1, round(words / 220))} min</div><div class="l">reading time</div></div>
              <div class="stat"><div class="n">{html.escape(st.session_state.language.capitalize())}</div><div class="l">spoken language</div></div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    st.download_button(
        "⬇ Download full report (.md)",
        data=build_report(result, st.session_state.source_label),
        file_name="video_report.md",
        mime="text/markdown",
    )
    st.write("")

    tab_sum, tab_act, tab_dec, tab_q, tab_tr, tab_chat = st.tabs(
        ["✨ Summary", "✅ Action items", "🔑 Decisions", "❓ Open questions", "📝 Transcript", "💬 Chat"]
    )

    with tab_sum:
        render_summary(result["summary"])

    with tab_act:
        render_cards(result["action_items"], "✅", "amber", "No action items found in this video.")

    with tab_dec:
        render_cards(result["key_decisions"], "🔑", "green", "No key decisions found in this video.")

    with tab_q:
        render_cards(result["open_questions"], "❓", "violet", "No open questions found in this video.")

    with tab_tr:
        q = st.text_input("Search transcript", placeholder="Type a word to highlight it…")
        st.markdown(transcript_html(result["transcript"], q), unsafe_allow_html=True)
        st.download_button(
            "⬇ Download transcript (.txt)",
            data=result["transcript"],
            file_name="transcript.txt",
            mime="text/plain",
        )

    with tab_chat:
        if not st.session_state.messages:
            st.caption("Try one of these, or type your own question below.")
            suggestions = [
                "Summarize this in 3 lines",
                "What are the next steps?",
                "Who is responsible for what?",
            ]
            cols = st.columns(len(suggestions))
            for col, s in zip(cols, suggestions):
                col.button(s, key=f"sug_{s}", on_click=set_pending, args=(s,), use_container_width=True)

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🤖"):
                st.markdown(msg["content"])

        typed = st.chat_input("Ask anything about this video…")
        question = typed or st.session_state.pop("pending_q", None)

        if question:
            st.session_state.messages.append({"role": "user", "content": question})
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(question)

            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Searching the transcript…"):
                    try:
                        answer = ask_question(result["rag_chain"], question)
                    except Exception as e:
                        answer = f"I couldn't answer that: {e}"
                st.markdown(answer)

            st.session_state.messages.append({"role": "assistant", "content": answer})
