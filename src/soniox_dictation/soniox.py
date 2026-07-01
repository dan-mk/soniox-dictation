from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable

import websockets

from .audio import AudioCaptureError, RawAudioProcess
from .config import Settings
from .soniox_async import save_recording_wav, transcribe_file


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


class _AudioCapture:
    """Captura o áudio guardando sempre uma cópia local completa da gravação.

    Enquanto `streaming` está ativo, os chunks também vão para a fila consumida
    pelo websocket em tempo real. Se a conexão cair, o streaming é desligado e a
    captura continua, permitindo transcrever a gravação pela rota assíncrona.
    """

    def __init__(self, settings: Settings, stop_event: threading.Event) -> None:
        self.settings = settings
        self.stop_event = stop_event
        self.recording = bytearray()
        self.queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self.streaming = True

    def stop_streaming(self) -> None:
        self.streaming = False
        while not self.queue.empty():
            self.queue.get_nowait()

    async def run(self) -> None:
        bytes_per_sample = 2
        chunk_ms = 120
        chunk_size = int(
            self.settings.sample_rate
            * self.settings.channels
            * bytes_per_sample
            * chunk_ms
            / 1000
        )
        try:
            async with RawAudioProcess(self.settings.audio_command) as audio:
                while not self.stop_event.is_set():
                    chunk = await audio.read(chunk_size)
                    self.recording.extend(chunk)
                    if self.streaming:
                        self.queue.put_nowait(chunk)
        finally:
            if self.streaming:
                self.queue.put_nowait(None)


async def _realtime_session(
    settings: Settings,
    capture: _AudioCapture,
    on_update: Callable[[str], None],
) -> str:
    accumulator = TranscriptAccumulator()

    async with websockets.connect(
        SONIOX_STT_URL,
        ping_interval=20,
        ping_timeout=20,
        max_size=8 * 1024 * 1024,
    ) as ws:
        await ws.send(json.dumps(_session_config(settings)))

        async def send_audio() -> None:
            while True:
                chunk = await capture.queue.get()
                if chunk is None:
                    await ws.send(json.dumps({"type": "finalize"}))
                    await ws.send("")
                    return
                await ws.send(chunk)

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
        try:
            done, pending = await asyncio.wait(
                {sender, receiver},
                return_when=asyncio.FIRST_EXCEPTION,
            )
            for task in done:
                task.result()
            if receiver in pending:
                await receiver
        finally:
            for task in (sender, receiver):
                if not task.done():
                    task.cancel()
            await asyncio.gather(sender, receiver, return_exceptions=True)

    return accumulator.final_text.strip()


async def _transcribe_recording_async(settings: Settings, pcm: bytes) -> str:
    if not pcm:
        return ""
    wav_path = save_recording_wav(settings, pcm)
    text = await asyncio.to_thread(transcribe_file, settings, wav_path)
    try:
        wav_path.unlink()
    except OSError:
        pass
    return text


async def transcribe_realtime(
    settings: Settings,
    stop_event: threading.Event,
    on_update: Callable[[str], None],
    on_fallback: Callable[[str], None] | None = None,
) -> str:
    capture = _AudioCapture(settings, stop_event)
    capture_task = asyncio.create_task(capture.run())

    async def fallback(reason: str) -> str:
        # Tempo real caiu: segue gravando até o usuário parar e depois
        # transcreve a gravação completa pela rota assíncrona.
        capture.stop_streaming()
        if on_fallback is not None:
            on_fallback(reason)
        try:
            await capture_task
        except AudioCaptureError:
            if not capture.recording:
                raise
        return await _transcribe_recording_async(settings, bytes(capture.recording))

    try:
        try:
            text = await _realtime_session(settings, capture, on_update)
        except (AudioCaptureError, asyncio.CancelledError):
            raise
        except Exception as exc:
            return await fallback(str(exc))

        if not capture_task.done() and not stop_event.is_set():
            return await fallback("conexão encerrada pelo servidor antes do fim da gravação")

        await capture_task
        return text
    finally:
        if not capture_task.done():
            capture_task.cancel()
            await asyncio.gather(capture_task, return_exceptions=True)
