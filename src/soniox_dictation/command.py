from __future__ import annotations

import argparse
import sys

from .ipc import IpcClientError, send_command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Controla uma instância do Soniox Dictation.")
    parser.add_argument("command", choices=["start", "stop", "toggle", "status", "quit"])
    args = parser.parse_args(argv)

    try:
        response = send_command(args.command)
    except IpcClientError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(response)
    return 0 if not response.startswith("error") else 2


if __name__ == "__main__":
    raise SystemExit(main())
