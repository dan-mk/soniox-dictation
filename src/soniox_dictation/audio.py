from __future__ import annotations

import asyncio


class AudioCaptureError(RuntimeError):
    pass


class RawAudioProcess:
    def __init__(self, command: list[str], debug: bool = False) -> None:
        self.command = command
        self.debug = debug
        self._process: asyncio.subprocess.Process | None = None

    async def __aenter__(self) -> "RawAudioProcess":
        self._process = await asyncio.create_subprocess_exec(
            *self.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    async def read(self, size: int) -> bytes:
        if self._process is None or self._process.stdout is None:
            raise AudioCaptureError("Captura de áudio não foi iniciada.")

        data = await self._process.stdout.read(size)
        if data:
            return data

        stderr = ""
        if self._process.stderr is not None:
            try:
                stderr_bytes = await asyncio.wait_for(self._process.stderr.read(), 0.2)
                stderr = stderr_bytes.decode(errors="replace").strip()
            except asyncio.TimeoutError:
                pass

        code = await self._process.wait()
        detail = f" Saída: {stderr}" if stderr else ""
        raise AudioCaptureError(f"Captura de áudio terminou cedo (código {code}).{detail}")

    async def stop(self) -> None:
        process = self._process
        if process is None or process.returncode is not None:
            return

        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), 1.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
