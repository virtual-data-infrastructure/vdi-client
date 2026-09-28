"""VDI command-line interface."""

import argparse
import sys

from vdi_client import __version__


def create_parser():
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

    subparsers.add_parser(
        "run",
        help="run the user program with the given user arguments",
    )

    subparsers.add_parser(
        "view",
        help="create, list and delete views",
    )

    return parser


def main(argv=None):
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
