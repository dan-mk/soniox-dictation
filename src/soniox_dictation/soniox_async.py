from __future__ import annotations

import io
import json
import os
import time
import uuid
import wave
from datetime import datetime
from pathlib import Path
from urllib import error, request

from .config import Settings

API_BASE = "https://api.soniox.com/v1"
UPLOAD_ATTEMPTS = 4
UPLOAD_RETRY_DELAY = 3.0
POLL_INTERVAL = 1.5
POLL_TIMEOUT = 300.0


class SonioxAsyncError(RuntimeError):
    pass


def recordings_dir() -> Path:
    base = Path(os.getenv("XDG_CACHE_HOME") or Path.home() / ".cache")
    path = base / "soniox-dictation" / "recordings"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_recording_wav(settings: Settings, pcm: bytes) -> Path:
    path = recordings_dir() / f"gravacao-{datetime.now():%Y%m%d-%H%M%S}.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(settings.channels)
        wav.setsampwidth(2)
        wav.setframerate(settings.sample_rate)
        wav.writeframes(pcm)
    return path


def _request(
    settings: Settings,
    method: str,
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> dict:
    req = request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {settings.api_key}")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with request.urlopen(req, timeout=timeout) as response:
        body = response.read()
    if not body:
        return {}
    parsed = json.loads(body)
    return parsed if isinstance(parsed, dict) else {}


def _http_error_detail(exc: error.HTTPError) -> str:
    try:
        body = exc.read().decode(errors="replace").strip()
    except OSError:
        body = ""
    return f"HTTP {exc.code}: {body or exc.reason}"


def _upload_file(settings: Settings, wav_path: Path) -> str:
    boundary = uuid.uuid4().hex
    payload = io.BytesIO()
    payload.write(f"--{boundary}\r\n".encode())
    payload.write(
        f'Content-Disposition: form-data; name="file"; filename="{wav_path.name}"\r\n'.encode()
    )
    payload.write(b"Content-Type: audio/wav\r\n\r\n")
    payload.write(wav_path.read_bytes())
    payload.write(f"\r\n--{boundary}--\r\n".encode())

    result = _request(
        settings,
        "POST",
        f"{API_BASE}/files",
        data=payload.getvalue(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=180.0,
    )
    file_id = result.get("id")
    if not file_id:
        raise SonioxAsyncError(f"Upload não retornou id de arquivo: {result!r}")
    return str(file_id)


def _upload_with_retries(settings: Settings, wav_path: Path) -> str:
    last_error: Exception | None = None
    for attempt in range(UPLOAD_ATTEMPTS):
        try:
            return _upload_file(settings, wav_path)
        except error.HTTPError as exc:
            if exc.code != 429 and exc.code < 500:
                raise SonioxAsyncError(_http_error_detail(exc)) from exc
            last_error = SonioxAsyncError(_http_error_detail(exc))
        except (error.URLError, OSError) as exc:
            last_error = exc
        if attempt + 1 < UPLOAD_ATTEMPTS:
            time.sleep(UPLOAD_RETRY_DELAY)
    raise SonioxAsyncError(f"Falha ao enviar a gravação: {last_error}")


def _delete_quietly(settings: Settings, url: str) -> None:
    try:
        _request(settings, "DELETE", url)
    except (error.URLError, OSError, ValueError):
        pass


def transcribe_file(settings: Settings, wav_path: Path) -> str:
    """Transcreve um WAV pela rota assíncrona (upload + polling)."""
    try:
        file_id = _upload_with_retries(settings, wav_path)
    except SonioxAsyncError as exc:
        raise SonioxAsyncError(
            f"{exc} Gravação preservada em: {wav_path}"
        ) from exc

    transcription_id: str | None = None
    try:
        body = {"file_id": file_id, "model": settings.async_model}
        if settings.language_hints:
            body["language_hints"] = settings.language_hints
        result = _request(
            settings,
            "POST",
            f"{API_BASE}/transcriptions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        transcription_id = result.get("id")
        if not transcription_id:
            raise SonioxAsyncError(f"Criação da transcrição não retornou id: {result!r}")

        deadline = time.monotonic() + POLL_TIMEOUT
        while True:
            status = _request(
                settings, "GET", f"{API_BASE}/transcriptions/{transcription_id}"
            )
            state = status.get("status")
            if state == "completed":
                break
            if state == "error":
                detail = status.get("error_message") or "erro desconhecido"
                raise SonioxAsyncError(f"Transcrição assíncrona falhou: {detail}")
            if time.monotonic() > deadline:
                raise SonioxAsyncError("Tempo esgotado aguardando a transcrição assíncrona.")
            time.sleep(POLL_INTERVAL)

        transcript = _request(
            settings, "GET", f"{API_BASE}/transcriptions/{transcription_id}/transcript"
        )
        return str(transcript.get("text") or "").strip()
    except error.HTTPError as exc:
        raise SonioxAsyncError(
            f"{_http_error_detail(exc)} Gravação preservada em: {wav_path}"
        ) from exc
    except (error.URLError, OSError) as exc:
        raise SonioxAsyncError(
            f"Erro de rede na transcrição assíncrona: {exc}. "
            f"Gravação preservada em: {wav_path}"
        ) from exc
    except SonioxAsyncError as exc:
        raise SonioxAsyncError(f"{exc} Gravação preservada em: {wav_path}") from exc
    finally:
        if transcription_id:
            _delete_quietly(settings, f"{API_BASE}/transcriptions/{transcription_id}")
        _delete_quietly(settings, f"{API_BASE}/files/{file_id}")
