# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""
VDI client - client tools for the virtual data infrastructure.

This module implements the command-line interface for the VDI client.
The CLI provides two subcommands:

- ``run``  : run a user program with VDI extensions (LD_PRELOAD)
- ``view`` : create, list and delete views on a VDI server

Subcommand implementations will be added in subsequent PRs.
"""

from __future__ import annotations

import argparse
import sys

from vdi_client import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create and return the top-level argument parser for the VDI CLI.

    Returns:
        The configured ``ArgumentParser`` instance.
    """
    parser = argparse.ArgumentParser(
        prog="vdi",
        description="Client tools for the virtual data infrastructure (VDI).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"vdi-client {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser(
        "run",
        help="run the user program with the given user arguments",
    )
    run_parser.add_argument(
        "program",
        nargs="?",
        help="path to program to be run",
    )
    run_parser.add_argument(
        "program_args",
        nargs=argparse.REMAINDER,
        help="any arguments to the program to be run",
    )

    subparsers.add_parser(
        "view",
        help="create, list and delete views",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the VDI CLI.

    Args:
        argv: Optional list of command-line arguments. If ``None``, ``sys.argv``
            is used (via ``argparse``).

    Returns:
        Process exit code (0 on success, non-zero on error).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    # Subcommand implementation will be added in PR 2.
    print(f"Subcommand '{args.command}' is not yet implemented.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
