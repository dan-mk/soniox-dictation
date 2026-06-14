from __future__ import annotations

import os
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str
    language_hints: list[str]
    sample_rate: int
    channels: int
    audio_command: list[str]
    debug: bool
    copy_only: bool
    restore_clipboard: bool
    inject_backend: str
    portal_paste_shortcut: str
    ydotool_command: str
    ydotool_socket: str | None


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} precisa ser um inteiro, recebido: {raw!r}") from exc


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on", "sim"}


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


def load_settings(debug: bool = False, copy_only: bool = False) -> Settings:
    load_dotenv(Path.cwd() / ".env")

    api_key = os.getenv("SONIOX_API_KEY")
    if not api_key:
        raise RuntimeError("SONIOX_API_KEY não encontrada no .env ou ambiente.")

    sample_rate = _int_env("SONIOX_SAMPLE_RATE", 16000)
    channels = _int_env("SONIOX_CHANNELS", 1)
    audio_command_env = os.getenv("SONIOX_AUDIO_COMMAND", "").strip()
    audio_command = (
        shlex.split(audio_command_env)
        if audio_command_env
        else _default_audio_command(sample_rate, channels)
    )

    portal_paste_shortcut = (
        os.getenv("SONIOX_PORTAL_PASTE_SHORTCUT", "ctrl+shift+v").strip().lower()
    )
    if portal_paste_shortcut not in {"ctrl+v", "ctrl+shift+v"}:
        raise ValueError(
            "SONIOX_PORTAL_PASTE_SHORTCUT precisa ser 'ctrl+v' ou 'ctrl+shift+v'."
        )

    inject_backend = os.getenv("SONIOX_INJECT_BACKEND", "portal").strip().lower()
    if inject_backend not in {"auto", "portal", "ydotool", "clipboard"}:
        raise ValueError(
            "SONIOX_INJECT_BACKEND precisa ser 'auto', 'portal', 'ydotool' ou 'clipboard'."
        )

    ydotool_socket = os.getenv("SONIOX_YDOTOOL_SOCKET", "").strip() or None
    ydotool_command = os.getenv("SONIOX_YDOTOOL_COMMAND", "ydotool").strip() or "ydotool"

    return Settings(
        api_key=api_key,
        model=os.getenv("SONIOX_MODEL", "stt-rt-v4").strip() or "stt-rt-v4",
        language_hints=_csv(os.getenv("SONIOX_LANGUAGE_HINTS", "pt,en")),
        sample_rate=sample_rate,
        channels=channels,
        audio_command=audio_command,
        debug=debug or _bool_env("SONIOX_DEBUG"),
        copy_only=copy_only or _bool_env("SONIOX_COPY_ONLY"),
        restore_clipboard=_bool_env("SONIOX_RESTORE_CLIPBOARD"),
        inject_backend=inject_backend,
        portal_paste_shortcut=portal_paste_shortcut,
        ydotool_command=ydotool_command,
        ydotool_socket=ydotool_socket,
    )
