"""Minimal CLI placeholder. A real subcommand layout will land in v0.1."""

from __future__ import annotations

import argparse
import sys

from pairo import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pairo", description="Pair records, smarter.")
    parser.add_argument("--version", action="version", version=f"pairo {__version__}")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("match", help="(stub) run a matching task; v0.1")
    args = parser.parse_args(argv)
    if args.cmd is None:
        parser.print_help()
        return 0
    print(f"command '{args.cmd}' not yet implemented — see v0.1.0", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
