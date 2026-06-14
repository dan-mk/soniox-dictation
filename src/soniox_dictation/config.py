from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

SUPPORTED_PASTE_SHORTCUTS = {"ctrl+v", "ctrl+shift+v"}
DEFAULT_PASTE_SHORTCUT = "ctrl+shift+v"
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str
    language_hints: list[str]
    sample_rate: int
    channels: int
    audio_command: list[str]
    ydotool_command: str
    ydotool_socket: str | None


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _default_audio_command(sample_rate: int, channels: int) -> list[str]:
    if shutil.which("parec"):
        return [
            "parec",
            "--format=s16le",
            f"--rate={sample_rate}",
            f"--channels={channels}",
            "--latency-msec=50",
        ]

    if shutil.which("arecord"):
        return [
            "arecord",
            "-q",
            "-f",
            "S16_LE",
            "-r",
            str(sample_rate),
            "-c",
            str(channels),
            "-t",
            "raw",
        ]

    raise RuntimeError(
        "Nenhum capturador de áudio encontrado. Instale 'pulseaudio-utils' "
        "(parec) ou 'alsa-utils' (arecord)."
    )


def load_settings() -> Settings:
    load_dotenv(Path.cwd() / ".env")

    api_key = os.getenv("SONIOX_API_KEY")
    if not api_key:
        raise RuntimeError("SONIOX_API_KEY não encontrada no .env ou ambiente.")

    sample_rate = DEFAULT_SAMPLE_RATE
    channels = DEFAULT_CHANNELS
    ydotool_socket = os.getenv("SONIOX_YDOTOOL_SOCKET", "").strip() or None
    ydotool_command = os.getenv("SONIOX_YDOTOOL_COMMAND", "ydotool").strip() or "ydotool"

    return Settings(
        api_key=api_key,
        model=os.getenv("SONIOX_MODEL", "stt-rt-v4").strip() or "stt-rt-v4",
        language_hints=_csv(os.getenv("SONIOX_LANGUAGE_HINTS", "pt,en")),
        sample_rate=sample_rate,
        channels=channels,
        audio_command=_default_audio_command(sample_rate, channels),
        ydotool_command=ydotool_command,
        ydotool_socket=ydotool_socket,
    )
