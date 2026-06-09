from __future__ import annotations

import os
import shutil
import subprocess
import time


class YdotoolKeyboardError(RuntimeError):
    pass


class YdotoolKeyboard:
    def __init__(
        self,
        command: str = "ydotool",
        socket_path: str | None = None,
    ) -> None:
        self.command = command
        self.socket_path = socket_path

    def paste(self, shortcut: str = "ctrl+v") -> None:
        command_path = shutil.which(self.command) or self.command
        if "/" not in command_path and not shutil.which(command_path):
            raise YdotoolKeyboardError(f"{self.command!r} não encontrado no PATH.")

        key_sequence = self._paste_sequence(shortcut)
        command = [
            command_path,
            "key",
            "-d",
            "60",
            *key_sequence,
        ]
        env = os.environ.copy()
        if self.socket_path:
            env["YDOTOOL_SOCKET"] = self.socket_path

        daemon_pids = self._ydotoold_pids()
        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
        except OSError as exc:
            raise YdotoolKeyboardError(f"Falha ao executar {self.command!r}: {exc}") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            if detail:
                raise YdotoolKeyboardError(detail) from exc
            raise YdotoolKeyboardError(
                f"'ydotool key' falhou com código {exc.returncode}."
            ) from exc

        if daemon_pids:
            time.sleep(0.2)
            current_pids = self._ydotoold_pids()
            if current_pids != daemon_pids:
                raise YdotoolKeyboardError(
                    "'ydotool key' retornou sucesso, mas o ydotoold caiu "
                    "após receber o comando."
                )

    @staticmethod
    def _ydotoold_pids() -> tuple[str, ...]:
        if not shutil.which("pgrep"):
            return ()
        result = subprocess.run(
            ["pgrep", "-x", "ydotoold"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if result.returncode not in {0, 1}:
            return ()
        return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())

    @staticmethod
    def _paste_sequence(shortcut: str) -> list[str]:
        if shortcut == "ctrl+v":
            return ["29:1", "47:1", "47:0", "29:0"]
        if shortcut == "ctrl+shift+v":
            return ["29:1", "42:1", "47:1", "47:0", "42:0", "29:0"]
        raise YdotoolKeyboardError(f"Atalho não suportado pelo ydotool: {shortcut!r}.")
