# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""
VDI client - command-line interface.

The CLI provides three subcommands:

- ``run``  : run a user program with VDI extensions (``LD_PRELOAD``)
- ``view`` : create, list, delete, inspect, upload to and remove files
             from views on a VDI server
- ``log``  : list, inspect and clean up VDI log files

Common arguments (accepted before the subcommand-specific arguments):

    --base-url   - base URL for VDI server to be accessed
    --config     - full path to config file [default: ``${HOME}/.vdi/config``]
    -h           - print usage for command
    -v           - verbose output
    --dry-run    - only print what the command would do without performing actions
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from vdi_client import __version__
from vdi_client.config import DEFAULT_CONFIG_PATH, load_config, resolve_base_url
from vdi_client.log import clean_logs, list_logs, show_log
from vdi_client.run import run as run_command
from vdi_client.view import (
    create_view,
    delete_view,
    get_url,
    list_files,
    list_views,
    remove_file,
    upload_file,
)


def _add_common_args(parser: argparse.ArgumentParser, *, suppress_defaults: bool = False) -> None:
    """Add common arguments shared by all subcommands.

    When *suppress_defaults* is ``True`` the arguments use
    :data:`argparse.SUPPRESS` as their default so that they do not
    overwrite values already set by a parent parser.
    """
    base_url_default: Any = argparse.SUPPRESS if suppress_defaults else None
    config_default: Any = argparse.SUPPRESS if suppress_defaults else None
    verbose_default: Any = argparse.SUPPRESS if suppress_defaults else False
    dry_run_default: Any = argparse.SUPPRESS if suppress_defaults else False

    parser.add_argument(
        "--base-url",
        default=base_url_default,
        help="base url for VDI server to be accessed",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=config_default,
        help="full path to config file [default: ${HOME}/.vdi/config]",
    )
    parser.add_argument(
        "-v",
        dest="verbose",
        action="store_true",
        default=verbose_default,
        help="verbose output",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=dry_run_default,
        help="only print what command would do without actually performing the actions",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create and return the top-level argument parser for the VDI CLI.

    Returns:
        The configured :class:`argparse.ArgumentParser` instance.
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

    # --- run subcommand ---
    run_parser = subparsers.add_parser(
        "run",
        help="run the user program with the given user arguments",
        description="Run the user program with the given user arguments.",
    )
    _add_common_args(run_parser)
    run_parser.add_argument(
        "--lib",
        dest="lib",
        default=None,
        help="path to libvdi.so (overrides VDI_LIB_PATH env var and default location)",
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

    # --- view subcommand ---
    view_parser = subparsers.add_parser(
        "view",
        help="create, list and delete views",
        description="Create, list and delete views on a VDI server.",
    )
    _add_common_args(view_parser)
    view_sub = view_parser.add_subparsers(dest="subcommand")

    create_p = view_sub.add_parser("create", help="create a new view")
    _add_common_args(create_p, suppress_defaults=True)
    create_p.add_argument("view_name", help="name of the view to be created")

    delete_p = view_sub.add_parser("delete", help="delete a view")
    _add_common_args(delete_p, suppress_defaults=True)
    delete_p.add_argument("view_name", help="name of the view to be deleted")

    files_p = view_sub.add_parser("files", help="list files in a view")
    _add_common_args(files_p, suppress_defaults=True)
    files_p.add_argument("view_name", help="name of the view to show the files it contains")

    geturl_p = view_sub.add_parser("geturl", help="print the download URL for a file in a view")
    _add_common_args(geturl_p, suppress_defaults=True)
    geturl_p.add_argument("view_name", help="name of the view that contains the file")
    geturl_p.add_argument("file_name", help="name of the file for which the URL should be shown")

    list_p = view_sub.add_parser("list", help="list all views")
    _add_common_args(list_p, suppress_defaults=True)

    remove_p = view_sub.add_parser("remove", help="remove a file from a view")
    _add_common_args(remove_p, suppress_defaults=True)
    remove_p.add_argument("view_name", help="name of the view that contains the file")
    remove_p.add_argument("file_name", help="name of the file to be removed from the view")

    upload_p = view_sub.add_parser("upload", help="upload a file to a view")
    _add_common_args(upload_p, suppress_defaults=True)
    upload_p.add_argument("view_name", help="name of the view")
    upload_p.add_argument("file_name", help="path to the file that should be uploaded to the view")

    # --- log subcommand ---
    log_parser = subparsers.add_parser(
        "log",
        help="list, show and clean up VDI log files",
        description="List, show and clean up VDI log files.",
    )
    _add_common_args(log_parser)
    log_parser.add_argument(
        "--log-dir",
        dest="log_dir",
        default=None,
        help="directory containing log files [default: $VDI_LOG_DIR or ~/.vdi/logs/]",
    )
    log_parser.add_argument(
        "--log-prefix",
        dest="log_prefix",
        default=None,
        help="prefix for log file names [default: $VDI_LOG_FILE_PREFIX or 'vdi_log.']",
    )
    log_sub = log_parser.add_subparsers(dest="subcommand")

    log_list_p = log_sub.add_parser("list", help="list log files")
    _add_common_args(log_list_p, suppress_defaults=True)
    log_list_p.add_argument(
        "--log-dir",
        dest="log_dir",
        default=argparse.SUPPRESS,
        help="directory containing log files [default: $VDI_LOG_DIR or ~/.vdi/logs/]",
    )
    log_list_p.add_argument(
        "--log-prefix",
        dest="log_prefix",
        default=argparse.SUPPRESS,
        help="prefix for log file names [default: $VDI_LOG_FILE_PREFIX or 'vdi_log.']",
    )
    log_list_p.add_argument(
        "--sort",
        dest="sort_key",
        choices=["pid", "date", "size", "program"],
        default="pid",
        help="sort log files by the given key [default: pid]",
    )
    log_list_p.add_argument(
        "-r",
        "--reverse",
        dest="reverse",
        action="store_true",
        default=False,
        help="reverse sort order",
    )
    log_list_p.add_argument(
        "--long",
        dest="long_format",
        action="store_true",
        default=False,
        help="show size, modification time and program name",
    )

    log_show_p = log_sub.add_parser("show", help="print the contents of a log file")
    _add_common_args(log_show_p, suppress_defaults=True)
    log_show_p.add_argument(
        "--log-dir",
        dest="log_dir",
        default=argparse.SUPPRESS,
        help="directory containing log files [default: $VDI_LOG_DIR or ~/.vdi/logs/]",
    )
    log_show_p.add_argument(
        "--log-prefix",
        dest="log_prefix",
        default=argparse.SUPPRESS,
        help="prefix for log file names [default: $VDI_LOG_FILE_PREFIX or 'vdi_log.']",
    )
    log_show_p.add_argument("pid", type=int, help="process ID of the log file to show")

    log_clean_p = log_sub.add_parser("clean", help="remove log files")
    _add_common_args(log_clean_p, suppress_defaults=True)
    log_clean_p.add_argument(
        "--log-dir",
        dest="log_dir",
        default=argparse.SUPPRESS,
        help="directory containing log files [default: $VDI_LOG_DIR or ~/.vdi/logs/]",
    )
    log_clean_p.add_argument(
        "--log-prefix",
        dest="log_prefix",
        default=argparse.SUPPRESS,
        help="prefix for log file names [default: $VDI_LOG_FILE_PREFIX or 'vdi_log.']",
    )
    log_clean_p.add_argument(
        "--pid",
        type=int,
        default=None,
        help="remove only the log file for this PID (default: remove all)",
    )

    return parser


def _handle_run(args: argparse.Namespace) -> int:
    """Dispatch the ``run`` subcommand."""
    return run_command(
        program=args.program,
        program_args=args.program_args,
        lib_override=args.lib,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def _handle_view(args: argparse.Namespace) -> int:
    """Dispatch the ``view`` subcommand and its sub-subcommands."""
    config = load_config(args.config if args.config is not None else DEFAULT_CONFIG_PATH)
    base_url = resolve_base_url(args.base_url, config)

    if args.subcommand is None:
        print("Error: no view subcommand specified.", file=sys.stderr)
        print(
            "Subcommands: create, delete, files, geturl, list, remove, upload",
            file=sys.stderr,
        )
        return 1

    # geturl does not require a server connection
    if args.subcommand == "geturl":
        if base_url is None:
            print(
                "Error: BASE_URL is not set. Provide it via --base-url or config file.",
                file=sys.stderr,
            )
            return 1
        return get_url(base_url, args.view_name, args.file_name)

    if base_url is None:
        print(
            "Error: BASE_URL is not set. Provide it via --base-url or config file.",
            file=sys.stderr,
        )
        return 1

    if args.subcommand == "create":
        return create_view(base_url, args.view_name, dry_run=args.dry_run, verbose=args.verbose)
    elif args.subcommand == "delete":
        return delete_view(base_url, args.view_name, dry_run=args.dry_run, verbose=args.verbose)
    elif args.subcommand == "files":
        return list_files(base_url, args.view_name, dry_run=args.dry_run, verbose=args.verbose)
    elif args.subcommand == "list":
        return list_views(base_url, dry_run=args.dry_run, verbose=args.verbose)
    elif args.subcommand == "remove":
        return remove_file(base_url, args.view_name, args.file_name, dry_run=args.dry_run, verbose=args.verbose)
    elif args.subcommand == "upload":
        return upload_file(base_url, args.view_name, args.file_name, dry_run=args.dry_run, verbose=args.verbose)

    print(f"Error: unknown view subcommand '{args.subcommand}'.", file=sys.stderr)
    return 1


def _handle_log(args: argparse.Namespace) -> int:
    """Dispatch the ``log`` subcommand and its sub-subcommands."""
    log_dir = getattr(args, "log_dir", None)
    log_prefix = getattr(args, "log_prefix", None)

    if args.subcommand is None:
        print("Error: no log subcommand specified.", file=sys.stderr)
        print("Subcommands: list, show, clean", file=sys.stderr)
        return 1

    if args.subcommand == "list":
        return list_logs(
            log_dir_override=log_dir,
            log_prefix_override=log_prefix,
            sort_key=args.sort_key,
            reverse=args.reverse,
            long_format=args.long_format,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    elif args.subcommand == "show":
        return show_log(
            args.pid,
            log_dir_override=log_dir,
            log_prefix_override=log_prefix,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    elif args.subcommand == "clean":
        return clean_logs(
            pid=args.pid,
            log_dir_override=log_dir,
            log_prefix_override=log_prefix,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

    print(f"Error: unknown log subcommand '{args.subcommand}'.", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    """Entry point for the VDI CLI.

    Args:
        argv: Optional list of command-line arguments. If ``None``,
            :data:`sys.argv` is used (via :mod:`argparse`).

    Returns:
        Process exit code (0 on success, non-zero on error).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "run":
        return _handle_run(args)
    elif args.command == "view":
        return _handle_view(args)
    elif args.command == "log":
        return _handle_log(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
