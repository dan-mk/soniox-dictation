from __future__ import annotations

import argparse
import sys

from .config import SUPPORTED_PASTE_SHORTCUTS
from .ipc import IpcClientError, send_command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Controla uma instância do Soniox Dictation.")
    parser.add_argument(
        "command",
        choices=["start", "stop", "cancel", "toggle", "status", "quit"],
    )
    parser.add_argument(
        "paste_shortcut",
        nargs="?",
        choices=sorted(SUPPORTED_PASTE_SHORTCUTS),
        help="atalho de colagem para start/toggle: ctrl+v ou ctrl+shift+v",
    )
    args = parser.parse_args(argv)

    if args.paste_shortcut and args.command not in {"start", "toggle"}:
        print("paste_shortcut só pode ser usado com start ou toggle.", file=sys.stderr)
        return 2

    command = args.command
    if args.paste_shortcut:
        command = f"{command} {args.paste_shortcut}"

    try:
        response = send_command(command)
    except IpcClientError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(response)
    return 0 if not response.startswith("error") else 2


if __name__ == "__main__":
    raise SystemExit(main())
