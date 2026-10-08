# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""
VDI client - ``log`` subcommand.

Provides subcommands to list, inspect and clean up VDI log files created
by ``libvdi.so`` during ``vdi run`` sessions.

Log files are written to the directory defined by the ``VDI_LOG_DIR``
environment variable (default: ``${HOME}/.vdi/logs/``) and use the naming
convention ``<prefix><pid>.log`` where ``<prefix>`` defaults to ``vdi_log.``
and can be overridden via ``VDI_LOG_FILE_PREFIX``.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# Environment variables that configure log file location and naming.
VDI_LOG_DIR_ENV = "VDI_LOG_DIR"
VDI_LOG_PREFIX_ENV = "VDI_LOG_FILE_PREFIX"

# Defaults matching the wrapper library behaviour.
DEFAULT_LOG_DIR = Path.home() / ".vdi" / "logs"
DEFAULT_LOG_PREFIX = "vdi_log."

# Pattern used to extract the PID from a log file name: <prefix><pid>.log
_LOG_NAME_RE_TEMPLATE = r"^{prefix}(\d+)\.log$"


@dataclass
class LogEntry:
    """Metadata for a single VDI log file.

    Attributes:
        pid: Process ID extracted from the file name.
        path: Full path to the log file.
        size: File size in bytes.
        mtime: Last modification time.
        program: Program name parsed from the first log line, or ``None``.
    """

    pid: int
    path: Path
    size: int
    mtime: float
    program: str | None


def resolve_log_dir(log_dir_override: str | None = None) -> Path:
    """Resolve the directory where VDI log files are stored.

    The lookup order is:

    1. Explicit ``log_dir_override`` (from ``--log-dir`` flag).
    2. ``VDI_LOG_DIR`` environment variable.
    3. ``${HOME}/.vdi/logs/`` (default).

    Args:
        log_dir_override: Optional explicit path passed on the command line.

    Returns:
        The resolved :class:`~pathlib.Path` to the log directory.
    """
    if log_dir_override:
        return Path(log_dir_override)
    env_dir = os.environ.get(VDI_LOG_DIR_ENV)
    if env_dir:
        return Path(env_dir)
    return DEFAULT_LOG_DIR


def resolve_log_prefix(log_prefix_override: str | None = None) -> str:
    """Resolve the prefix used for VDI log file names.

    The lookup order is:

    1. Explicit ``log_prefix_override`` (from ``--log-prefix`` flag).
    2. ``VDI_LOG_FILE_PREFIX`` environment variable.
    3. ``vdi_log.`` (default).

    Args:
        log_prefix_override: Optional explicit prefix passed on the command line.

    Returns:
        The resolved prefix string.
    """
    if log_prefix_override is not None:
        return log_prefix_override
    return os.environ.get(VDI_LOG_PREFIX_ENV, DEFAULT_LOG_PREFIX)


def _parse_pid_from_name(filename: str, prefix: str) -> int | None:
    """Extract the PID from a log file name.

    Args:
        filename: The file name (without directory).
        prefix: The log file name prefix.

    Returns:
        The PID as an int, or ``None`` if the name does not match.
    """
    escaped_prefix = re.escape(prefix)
    match = re.match(_LOG_NAME_RE_TEMPLATE.format(prefix=escaped_prefix), filename)
    if match:
        return int(match.group(1))
    return None


def _parse_program_from_log(path: Path) -> str | None:
    """Extract the program name from the first line of a log file.

    The log file format stores the command line (including the program name)
    in column 10, with arguments separated by ``%%``.  The program name is
    the first element of that column.

    Args:
        path: Path to the log file.

    Returns:
        The program name, or ``None`` if it cannot be determined.
    """
    try:
        with path.open("r", encoding="utf-8", errors="replace") as file:
            first_line = file.readline()
    except OSError:
        return None

    if not first_line.strip():
        return None

    # Columns are separated by spaces; column 10 (0-indexed: 9) is the
    # command line. We split on whitespace but need to be careful because
    # the command-line column itself uses %% as separator (no spaces).
    # The log format uses space-delimited columns.
    parts = first_line.split()
    if len(parts) < 10:
        return None

    cmd_column = parts[9]
    # The command line column uses %% to separate arguments.
    cmd_parts = cmd_column.split("%%")
    if not cmd_parts:
        return None

    # The program name is the first element; strip any ## that replace spaces.
    program = cmd_parts[0].replace("##", " ")
    return program if program else None


def collect_log_entries(
    log_dir: Path,
    prefix: str,
) -> list[LogEntry]:
    """Collect metadata for all log files in a directory.

    Args:
        log_dir: Directory to scan for log files.
        prefix: Log file name prefix to match.

    Returns:
        A list of :class:`LogEntry` objects, unsorted.
    """
    entries: list[LogEntry] = []
    if not log_dir.is_dir():
        return entries

    for item in log_dir.iterdir():
        if not item.is_file():
            continue
        pid = _parse_pid_from_name(item.name, prefix)
        if pid is None:
            continue
        try:
            stat = item.stat()
        except OSError:
            continue
        entries.append(
            LogEntry(
                pid=pid,
                path=item,
                size=stat.st_size,
                mtime=stat.st_mtime,
                program=_parse_program_from_log(item),
            )
        )
    return entries


def _sort_entries(
    entries: list[LogEntry],
    sort_key: str,
    reverse: bool,
) -> list[LogEntry]:
    """Sort log entries by the given key.

    Args:
        entries: List of log entries to sort.
        sort_key: One of ``pid``, ``date``, ``size``, ``program``.
        reverse: If ``True``, sort in descending order.

    Returns:
        A new sorted list.
    """
    sort_functions: dict[str, Callable[[LogEntry], Any]] = {
        "date": lambda entry: entry.mtime,
        "size": lambda entry: entry.size,
        "program": lambda entry: (entry.program is None, entry.program or ""),
        "pid": lambda entry: entry.pid,
    }
    key_func = sort_functions.get(sort_key, sort_functions["pid"])

    return sorted(entries, key=key_func, reverse=reverse)


def _format_size(size: int) -> str:
    """Format a byte count into a human-readable string."""
    for unit in ("B", "K", "M", "G", "T"):
        if size < 1024:
            return f"{size}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024  # type: ignore[assignment]
    return f"{size:.1f}P"


def _format_mtime(mtime: float) -> str:
    """Format a modification timestamp into a human-readable string."""
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")


def list_logs(
    *,
    log_dir_override: str | None = None,
    log_prefix_override: str | None = None,
    sort_key: str = "pid",
    reverse: bool = False,
    long_format: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """List VDI log files.

    Args:
        log_dir_override: Optional explicit log directory path.
        log_prefix_override: Optional explicit log file name prefix.
        sort_key: Sort key which is one of ``pid``, ``date``, ``size``, ``program``.
        reverse: If ``True``, reverse the sort order.
        long_format: If ``True``, show size, date and program name.
        dry_run: If ``True``, print what would be done without scanning files.
        verbose: If ``True``, print extra diagnostic information.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    log_dir = resolve_log_dir(log_dir_override)
    prefix = resolve_log_prefix(log_prefix_override)

    if dry_run:
        print(f"dry-run: list logs in '{log_dir}' (prefix='{prefix}', sort='{sort_key}')")
        return 0

    if verbose:
        print(f"Listing logs in '{log_dir}' (prefix='{prefix}')")

    if not log_dir.is_dir():
        print(f"No log directory found at '{log_dir}'.")
        return 0

    entries = collect_log_entries(log_dir, prefix)
    entries = _sort_entries(entries, sort_key, reverse)

    if not entries:
        print(f"No log files found in '{log_dir}'.")
        return 0

    if long_format:
        print(f"{'PID':>10}  {'Size':>8}  {'Modified':<19}  Program")
        print(f"{'---':>10}  {'----':>8}  {'--------':<19}  -------")
        for entry in entries:
            program = entry.program or "?"
            print(f"{entry.pid:>10}  {_format_size(entry.size):>8}  {_format_mtime(entry.mtime):<19}  {program}")
    else:
        for entry in entries:
            print(f"{entry.pid:>10}  {entry.path.name}")

    return 0


def show_log(
    pid: int,
    *,
    log_dir_override: str | None = None,
    log_prefix_override: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Print the contents of a specific VDI log file.

    Args:
        pid: Process ID of the log file to show.
        log_dir_override: Optional explicit log directory path.
        log_prefix_override: Optional explicit log file name prefix.
        dry_run: If ``True``, print what would be done without reading the file.
        verbose: If ``True``, print extra diagnostic information.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    log_dir = resolve_log_dir(log_dir_override)
    prefix = resolve_log_prefix(log_prefix_override)
    log_path = log_dir / f"{prefix}{pid}.log"

    if dry_run:
        print(f"dry-run: show log '{log_path}'")
        return 0

    if verbose:
        print(f"Showing log '{log_path}'")

    if not log_path.is_file():
        print(f"Error: log file not found: '{log_path}'", file=sys.stderr)
        return 1

    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as file:
            for line in file:
                print(line, end="")
    except OSError as exc:
        print(f"Error: failed to read '{log_path}': {exc}", file=sys.stderr)
        return 1

    return 0


def clean_logs(
    *,
    pid: int | None = None,
    log_dir_override: str | None = None,
    log_prefix_override: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Remove VDI log files.

    Args:
        pid: If given, remove only the log file for this PID. If ``None``,
            remove all log files.
        log_dir_override: Optional explicit log directory path.
        log_prefix_override: Optional explicit log file name prefix.
        dry_run: If ``True``, print what would be done without deleting files.
        verbose: If ``True``, print extra diagnostic information.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    log_dir = resolve_log_dir(log_dir_override)
    prefix = resolve_log_prefix(log_prefix_override)

    if pid is not None:
        log_path = log_dir / f"{prefix}{pid}.log"
        if dry_run:
            print(f"dry-run: remove log '{log_path}'")
            return 0
        if verbose:
            print(f"Removing log '{log_path}'")
        if not log_path.is_file():
            print(f"Error: log file not found: '{log_path}'", file=sys.stderr)
            return 1
        try:
            log_path.unlink()
        except OSError as exc:
            print(f"Error: failed to remove '{log_path}': {exc}", file=sys.stderr)
            return 1
        print(f"Removed log '{log_path}'.")
        return 0

    if dry_run:
        entries = collect_log_entries(log_dir, prefix)
        print(f"dry-run: remove {len(entries)} log file(s) from '{log_dir}'")
        for entry in entries:
            print(f"  would remove: {entry.path.name}")
        return 0

    if verbose:
        print(f"Removing all logs from '{log_dir}' (prefix='{prefix}')")

    if not log_dir.is_dir():
        print(f"No log directory found at '{log_dir}'.")
        return 0

    entries = collect_log_entries(log_dir, prefix)
    if not entries:
        print(f"No log files found in '{log_dir}'.")
        return 0

    removed = 0
    errors = 0
    for entry in entries:
        try:
            entry.path.unlink()
            removed += 1
            if verbose:
                print(f"  removed: {entry.path.name}")
        except OSError as exc:
            print(f"Error: failed to remove '{entry.path}': {exc}", file=sys.stderr)
            errors += 1

    print(f"Removed {removed} log file(s) from '{log_dir}'.")
    if errors:
        return 1
    return 0
    