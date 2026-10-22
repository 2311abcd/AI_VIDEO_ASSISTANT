import os

import yt_dlp
from pydub import AudioSegment

DOWNLOAD_DIR = 'downloades'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

COOKIES_PATH = "/tmp/yt_cookies.txt"


def _cookie_options() -> dict:
    """
    Cookies ka order:
    1. YT_COOKIES (secret/env me cookies.txt ka poora text) ho to woh use hoga (server).
    2. Warna local laptop par Chrome ki cookies (pehle jaisa).
    Chrome na mile (server) to download_youtube_audio bina cookies ke dobara try karta hai.
    """
    cookies_text = os.getenv("YT_COOKIES")
    if cookies_text and cookies_text.strip():
        with open(COOKIES_PATH, "w") as f:
            f.write(cookies_text.strip() + "\n")
        return {"cookiefile": COOKIES_PATH}
    return {"cookiesfrombrowser": ("chrome",)}


def _base_opts() -> dict:
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    return {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "remote_components": ["ejs:github"],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
    }


def _download(url: str, extra: dict) -> str:
    with yt_dlp.YoutubeDL({**_base_opts(), **extra}) as ydl:
        info = ydl.extract_info(url, download=True)
        return os.path.splitext(ydl.prepare_filename(info))[0] + ".wav"


def download_youtube_audio(url: str) -> str:
    try:
        return _download(url, _cookie_options())
    except Exception as first_error:
        # Server par Chrome nahi hota -> bina cookies ke ek baar aur try
        if "cookiesfrombrowser" in _cookie_options() or "chrome" in str(first_error).lower():
            return _download(url, {})
        raise


def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)  # 16khz
    audio.export(output_path, format="wav")
    return output_path


def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000

    chunks = []

    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start: start + chunk_ms]
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")

        chunks.append(chunk_path)

    return chunks


def process_input(source: str) -> list:
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")
    return chunks

