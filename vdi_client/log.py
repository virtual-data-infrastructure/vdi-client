# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""
VDI client - ``log`` subcommand.

Provides subcommands to list, inspect and clean up VDI log files created
by ``libvdi.so`` during ``vdi run`` sessions.

Log file location and naming configuration (``VDI_LOG_DIR``,
``VDI_LOG_FILE_PREFIX`` and their defaults) is defined in
:mod:`vdi_client.config`.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote

from vdi_client.config import resolve_log_dir, resolve_log_prefix
from vdi_client.run import detect_eessi_version

_LOG_NAME_RE_TEMPLATE = r"^{prefix}(\d+)\.log$"
_EESSI_VERSION_RE = re.compile(r"^\d{4}\.\d{2}$")


def _decode_log_value(value: str) -> str:
    """Decode a percent-encoded VDI log value.

    Malformed sequences are left unchanged.

    Args:
        value: Encoded value read from a VDI log file.

    Returns:
        The decoded value.
    """
    return unquote(value)


@dataclass
class LogEntry:
    """Metadata for a single VDI log file.

    Attributes:
        pid: Process ID extracted from the file name.
        path: Full path to the log file.
        size: File size in bytes.
        mtime: Last modification time.
        program: Program name parsed from the first log line, or ``None``.
        eessi_version: EESSI version parsed from the first log line.
    """

    pid: int
    path: Path
    size: int
    mtime: float
    program: str | None
    eessi_version: str


def _parse_log_metadata(path: Path) -> tuple[str | None, str]:
    """Parse metadata from the first line of a log file.

    Old-format logs have no EESSI version field and are reported as ``unknown``.

    Args:
        path: Path to the log file.

    Returns:
        The program name (or ``None``) and EESSI version.
    """
    try:
        with path.open("r", encoding="utf-8", errors="replace") as file:
            first_line = file.readline()
    except OSError:
        return None, "unknown"

    parts = first_line.split()
    if len(parts) < 10:
        return None, "unknown"

    cmd_parts = parts[9].split("%%")
    program = _decode_log_value(cmd_parts[0]) if cmd_parts else None

    eessi_version = "unknown"
    if len(parts) > 12:
        candidate = _decode_log_value(parts[12])
        if candidate == "unknown" or _EESSI_VERSION_RE.fullmatch(candidate):
            eessi_version = candidate

    return (program or None), eessi_version


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
        program, eessi_version = _parse_log_metadata(item)
        entries.append(
            LogEntry(
                pid=pid,
                path=item,
                size=stat.st_size,
                mtime=stat.st_mtime,
                program=program,
                eessi_version=eessi_version,
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


def _select_entries(
    entries: list[LogEntry],
    eessi_version_override: str | None,
    all_versions: bool,
) -> tuple[list[LogEntry], str | None, int]:
    """Select log entries using the requested EESSI-version policy.

    Args:
        entries: All collected log entries.
        eessi_version_override: Explicit version to match, if any.
        all_versions: Whether to bypass default filtering.

    Returns:
        Selected entries, applied filter, and number of hidden entries.
    """
    if eessi_version_override is not None:
        version_filter = eessi_version_override
    elif all_versions or (active_version := detect_eessi_version()) is None:
        return entries, None, 0
    else:
        version_filter = active_version

    selected = [entry for entry in entries if entry.eessi_version == version_filter]
    return selected, version_filter, len(entries) - len(selected)


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
    eessi_version_override: str | None = None,
    all_versions: bool = False,
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
        eessi_version_override: Optional explicit EESSI version to show.
        all_versions: If ``True``, bypass default EESSI-version filtering.
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

    all_entries = collect_log_entries(log_dir, prefix)
    entries, version_filter, hidden_count = _select_entries(
        all_entries,
        eessi_version_override,
        all_versions,
    )
    entries = _sort_entries(entries, sort_key, reverse)

    if not entries:
        if version_filter is None:
            print(f"No log files found in '{log_dir}'.")
        else:
            print(f"No log files found for EESSI {version_filter} in '{log_dir}'.")
        return 0

    if long_format:
        print(f"{'PID':>10}  {'Size':>8}  {'Modified':<19}  {'EESSI':<7}  Program")
        print(f"{'---':>10}  {'----':>8}  {'--------':<19}  {'-----':<7}  -------")
        for entry in entries:
            program = entry.program or "?"
            print(
                f"{entry.pid:>10}  {_format_size(entry.size):>8}  "
                f"{_format_mtime(entry.mtime):<19}  {entry.eessi_version:<7}  {program}"
            )
    else:
        print(f"{'PID':>10}  {'EESSI':<7}  File")
        print(f"{'---':>10}  {'-----':<7}  ----")
        for entry in entries:
            print(f"{entry.pid:>10}  {entry.eessi_version:<7}  {entry.path.name}")

    uses_default_filter = eessi_version_override is None and not all_versions
    if hidden_count and uses_default_filter:
        print(
            f"Showing logs for EESSI {version_filter}; {hidden_count} other log(s) available "
            "(use --eessi-version to filter, or --all to show all)"
        )

    return 0


def show_log(
    pid: int,
    *,
    log_dir_override: str | None = None,
    log_prefix_override: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    eessi_version_override: str | None = None,
    all_versions: bool = False,
) -> int:
    """Print the contents of a specific VDI log file.

    Args:
        pid: Process ID of the log file to show.
        log_dir_override: Optional explicit log directory path.
        log_prefix_override: Optional explicit log file name prefix.
        dry_run: If ``True``, print what would be done without reading the file.
        verbose: If ``True``, print extra diagnostic information.
        eessi_version_override: Optional explicit EESSI version to show.
        all_versions: If ``True``, bypass default EESSI-version filtering.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    log_dir = resolve_log_dir(log_dir_override)
    prefix = resolve_log_prefix(log_prefix_override)
    entries = collect_log_entries(log_dir, prefix)
    selected, version_filter, _ = _select_entries(
        entries,
        eessi_version_override,
        all_versions,
    )
    matching_entry = next((entry for entry in selected if entry.pid == pid), None)
    if matching_entry is None:
        log_path = log_dir / f"{prefix}{pid}.log"
        if not dry_run:
            print(f"Error: log file not found: '{log_path}'", file=sys.stderr)
            return 1
    else:
        log_path = matching_entry.path

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
