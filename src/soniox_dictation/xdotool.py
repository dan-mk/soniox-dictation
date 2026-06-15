from __future__ import annotations

import shutil
import subprocess


class XdotoolKeyboardError(RuntimeError):
    pass


_SUPPORTED_SHORTCUTS = {"ctrl+v", "ctrl+shift+v"}


class XdotoolKeyboard:
    def __init__(self, command: str = "xdotool") -> None:
        self.command = command

    def _resolve_command(self) -> str:
        command_path = shutil.which(self.command) or self.command
        if "/" not in command_path and not shutil.which(command_path):
            raise XdotoolKeyboardError(f"{self.command!r} não encontrado no PATH.")
        return command_path

    def capture_active_window(self) -> str | None:
        """Retorna o id da janela focada agora, ou None se não der pra obter."""
        try:
            command_path = self._resolve_command()
        except XdotoolKeyboardError:
            return None
        result = subprocess.run(
            [command_path, "getactivewindow"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        window_id = result.stdout.strip()
        if result.returncode != 0 or not window_id:
            return None
        return window_id

    def paste(self, shortcut: str = "ctrl+v", target_window: str | None = None) -> None:
        if shortcut not in _SUPPORTED_SHORTCUTS:
            raise XdotoolKeyboardError(f"Atalho não suportado pelo xdotool: {shortcut!r}.")

        command_path = self._resolve_command()

        command = [command_path]
        if target_window:
            # Reativa a janela alvo antes de colar; depois que o overlay some,
            # o Mutter pode deixar o foco em nenhuma janela (active window 0x0).
            command += ["windowactivate", "--sync", target_window]
        command += ["key", "--clearmodifiers", shortcut]

        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            raise XdotoolKeyboardError(f"Falha ao executar {self.command!r}: {exc}") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            if detail:
                raise XdotoolKeyboardError(detail) from exc
            raise XdotoolKeyboardError(
                f"'xdotool key' falhou com código {exc.returncode}."
            ) from exc
