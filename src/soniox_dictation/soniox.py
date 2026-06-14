from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable

import websockets

from .audio import RawAudioProcess
from .config import Settings


SONIOX_STT_URL = "wss://stt-rt.soniox.com/transcribe-websocket"
CONTROL_MARKERS = {"<end>", "<fin>"}


class SonioxRealtimeError(RuntimeError):
    pass


class TranscriptAccumulator:
    def __init__(self) -> None:
        self._final_parts: list[str] = []
        self._partial = ""

    @property
    def final_text(self) -> str:
        return "".join(self._final_parts)

    @property
    def display_text(self) -> str:
        return self.final_text + self._partial

    def accept(self, tokens: list[dict]) -> None:
        partial_parts: list[str] = []
        for token in tokens:
            text = str(token.get("text", ""))
            if text in CONTROL_MARKERS:
                continue
            if token.get("is_final"):
                self._final_parts.append(text)
            else:
                partial_parts.append(text)
        self._partial = "".join(partial_parts)


def _session_config(settings: Settings) -> dict:
    config = {
        "api_key": settings.api_key,
        "model": settings.model,
        "audio_format": "pcm_s16le",
        "sample_rate": settings.sample_rate,
        "num_channels": settings.channels,
    }
    if settings.language_hints:
        config["language_hints"] = settings.language_hints
    return config


async def transcribe_realtime(
    settings: Settings,
    stop_event: threading.Event,
    on_update: Callable[[str], None],
) -> str:
    accumulator = TranscriptAccumulator()
    bytes_per_sample = 2
    chunk_ms = 120
    chunk_size = int(
        settings.sample_rate * settings.channels * bytes_per_sample * chunk_ms / 1000
    )

    async with websockets.connect(
        SONIOX_STT_URL,
        ping_interval=20,
        ping_timeout=20,
        max_size=8 * 1024 * 1024,
    ) as ws:
        await ws.send(json.dumps(_session_config(settings)))

        async def send_audio() -> None:
            async with RawAudioProcess(settings.audio_command) as audio:
                while not stop_event.is_set():
                    chunk = await audio.read(chunk_size)
                    await ws.send(chunk)

                await ws.send(json.dumps({"type": "finalize"}))
                await ws.send("")

        async def receive_results() -> None:
            while True:
                try:
                    raw_message = await ws.recv()
                except websockets.ConnectionClosedOK:
                    return

                if isinstance(raw_message, bytes):
                    continue

                message = json.loads(raw_message)
                error_type = message.get("error_type") or message.get("error_code")
                if error_type:
                    detail = message.get("message") or message.get("error_message") or error_type
                    raise SonioxRealtimeError(str(detail))

                tokens = message.get("tokens") or []
                if tokens:
                    accumulator.accept(tokens)
                    on_update(accumulator.display_text.strip())

                if message.get("finished"):
                    return

        sender = asyncio.create_task(send_audio())
        receiver = asyncio.create_task(receive_results())
        done, pending = await asyncio.wait(
            {sender, receiver},
            return_when=asyncio.FIRST_EXCEPTION,
        )

        for task in done:
            task.result()

        if receiver in pending:
            await receiver
        if sender in pending:
            sender.cancel()
            try:
                await sender
            except asyncio.CancelledError:
                pass

    return accumulator.final_text.strip()
