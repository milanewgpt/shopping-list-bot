"""Voice message transcription via Google Speech Recognition (free, no API key)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import speech_recognition as sr

from bot.config import FFMPEG_PATH, TEMP_DIR, logger


async def transcribe_voice(ogg_path: Path) -> str:
    """Convert OGG to WAV, then transcribe with Google Speech Recognition."""
    wav_path = ogg_path.with_suffix(".wav")
    try:
        _ogg_to_wav(ogg_path, wav_path)
        text = _recognize_wav(wav_path)
        logger.info("Transcription result: %s", text)
        return text
    finally:
        wav_path.unlink(missing_ok=True)


async def download_voice(voice_file, bot) -> Path:
    """Download a Telegram voice message to a temp file."""
    dest = TEMP_DIR / f"voice_{voice_file.file_unique_id}.ogg"
    tg_file = await bot.get_file(voice_file.file_id)
    await tg_file.download_to_drive(str(dest))
    logger.info("Voice downloaded to %s", dest)
    return dest


def _ogg_to_wav(src: Path, dst: Path) -> None:
    """Convert OGG/Opus to 16 kHz mono WAV using bundled ffmpeg."""
    cmd = [
        FFMPEG_PATH, "-y", "-i", str(src),
        "-ar", "16000", "-ac", "1", "-f", "wav", str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode != 0:
        logger.error("ffmpeg stderr: %s", result.stderr.decode(errors="replace"))
        raise RuntimeError("ffmpeg conversion failed")


def _recognize_wav(wav_path: Path) -> str:
    """Transcribe WAV file using Google free Speech Recognition."""
    recognizer = sr.Recognizer()
    with sr.AudioFile(str(wav_path)) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio, language="ru-RU")
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        logger.error("Google Speech Recognition error: %s", e)
        raise
    return text.strip()
